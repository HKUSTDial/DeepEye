from __future__ import annotations

import json
import uuid
import os

from deepeye.tools.base import tool
from deepeye.tools.planning_tools import create_plan, mark_step_done, update_plan
from app.db.session import SessionLocal
from app.repositories import SessionRepository
from app.services.workflow_file_service import service_run_workflow_from_file
from app.sandbox import sandbox_manager
from deepeye.agents import WorkflowAgent
from deepeye.utils.logger import logger
from deepeye.workflows.models import Graph

WORKFLOW_DIR = "/workspace/workflow"


def _get_session(db, session_id: str):
    try:
        session_uuid = uuid.UUID(session_id)
    except (TypeError, ValueError):
        logger.warning("[workflow_tools] Invalid session_id=%s", session_id)
        return None
    return SessionRepository(db).get(session_uuid)


def _sanitize_workflow_name(name: str) -> str:
    base = name.strip()
    if base.lower().endswith(".json"):
        base = base[:-5]
    clean = "".join(ch for ch in base if ch.isalnum() or ch in ("-", "_"))
    if not clean:
        clean = "workflow"
    return f"{clean}.json"


def _build_workflow_path(name: str) -> str:
    return f"{WORKFLOW_DIR}/{_sanitize_workflow_name(name)}"

def _normalize_workflow_path(path: str) -> str:
    """Normalize path to always be under WORKFLOW_DIR."""
    if not isinstance(path, str):
        return path
    clean = path.strip()
    # Extract basename to ignore agent-provided subdirectories or wrong roots
    filename = os.path.basename(clean)
    return f"{WORKFLOW_DIR}/{_sanitize_workflow_name(filename)}"


async def _read_workflow_file(session_id: str, path: str) -> dict:
    sandbox = await sandbox_manager.get_or_create_sandbox(session_id)
    if not sandbox:
        raise ValueError("failed to get or create sandbox")
    result = await sandbox.exec_command(f"cat {path}")
    if result.exit_code != 0:
        raise ValueError(result.stderr or "failed to read workflow file")
    if not result.stdout.strip():
        raise ValueError("workflow file is empty")
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid workflow json: {exc}") from exc


async def _write_workflow_path(session_id: str, path: str, data: dict) -> None:
    sandbox = await sandbox_manager.get_or_create_sandbox(session_id)
    if not sandbox:
        raise ValueError("failed to get or create sandbox")
    await sandbox.exec_command(f"mkdir -p {WORKFLOW_DIR}")
    payload = json.dumps(data, ensure_ascii=False, indent=2)
    result = await sandbox.exec_command(f"cat > {path} << 'EOF'\n{payload}\nEOF")
    if result.exit_code != 0:
        raise ValueError(result.stderr or "failed to write workflow file")


def create_create_workflow_tool(session_id: str) -> callable:
    @tool
    async def create_workflow(file_path: str, workflow: dict) -> dict:
        """
        Create or replace a full workflow JSON file.

        Args:
            file_path: Path to the workflow JSON file (e.g. student_count.json)
            workflow: The full workflow definition object
        """
        norm_path = _normalize_workflow_path(file_path)
        await _write_workflow_path(session_id, norm_path, workflow)
        return {"status": "success", "file_path": norm_path}

    return create_workflow


def create_read_workflow_tool(session_id: str) -> callable:
    @tool
    async def read_workflow(file_path: str) -> dict:
        """
        Read an existing workflow JSON file.

        Args:
            file_path: Path to the workflow JSON file
        """
        norm_path = _normalize_workflow_path(file_path)
        try:
            workflow = await _read_workflow_file(session_id, norm_path)
            return {"status": "success", "workflow": workflow, "file_path": norm_path}
        except Exception as exc:
            return {"status": "error", "error": str(exc), "file_path": norm_path}

    return read_workflow


def create_update_workflow_tool(session_id: str) -> callable:
    @tool
    async def update_workflow(file_path: str, workflow: dict) -> dict:
        """
        Update (overwrite) an existing workflow JSON file.

        Args:
            file_path: Path to the workflow JSON file
            workflow: The full workflow definition object
        """
        norm_path = _normalize_workflow_path(file_path)
        await _write_workflow_path(session_id, norm_path, workflow)
        return {"status": "success", "file_path": norm_path}

    return update_workflow


def create_run_workflow_from_file_tool(session_id: str) -> callable:
    @tool
    async def run_workflow_from_file(file_path: str) -> dict:
        """
        Run a workflow JSON from the sandbox file system.

        Args:
            file_path: Path to the workflow JSON file
        """
        norm_path = _normalize_workflow_path(file_path)
        db = SessionLocal()
        try:
            session = _get_session(db, session_id)
            if not session:
                return {"status": "error", "error": "Session not found."}
            result = await service_run_workflow_from_file(db, session.user_id, session_id, norm_path)
            return result
        finally:
            db.close()

    return run_workflow_from_file


def create_design_workflow_tool(model, session_id: str, system_prompt: str, callbacks: list | None = None) -> callable:
    @tool
    async def workflow_agent(goal: str) -> str:
        """
        Workflow Designer Agent: design, iterate, and run data analysis workflows.
        Pass a clear analysis goal and any relevant data context.
        """
        db = SessionLocal()
        try:
            session = _get_session(db, session_id)
            if not session:
                return "Session not found."
            workflow_agent_inst = WorkflowAgent(
                model=model,
                system_prompt=system_prompt,
                tools=[
                    create_plan,
                    update_plan,
                    mark_step_done,
                    create_create_workflow_tool(session_id),
                    create_read_workflow_tool(session_id),
                    create_update_workflow_tool(session_id),
                    create_run_workflow_from_file_tool(session_id),
                ],
            )
            result = await workflow_agent_inst.ainvoke(
                goal,
                thread_id=f"workflow_agent_{session_id}",
                config={"callbacks": callbacks},
            )
            messages = result.get("messages", [])
            return messages[-1].content if messages else ""
        finally:
            db.close()

    return workflow_agent
