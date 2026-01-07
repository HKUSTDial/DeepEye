from __future__ import annotations

import json
import uuid

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
    clean = path.strip()
    if clean.startswith("/"):
        return clean
    return _build_workflow_path(clean)

def _extract_path_from_payload(payload: dict | None) -> str | None:
    if not isinstance(payload, dict):
        return None
    raw = payload.get("file_path") or payload.get("path") or payload.get("name")
    if not isinstance(raw, str) or not raw.strip():
        return None
    cleaned = raw.strip()
    if cleaned.startswith("/"):
        return cleaned
    return _build_workflow_path(cleaned)


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
    async def create_workflow(payload: dict) -> str:
        """
        Create or replace a full workflow JSON file.

        Payload (structured frame):
        {
          "file_path": "/workspace/workflow/xxx.json",
          "workflow": { "root": { "nodes": {...}, "edges": {...} } }
        }
        """
        if not isinstance(payload, dict):
            return "Invalid payload: expected JSON object."
        path = _extract_path_from_payload(payload)
        if not path:
            return "Invalid payload: file_path is required."
        workflow = payload.get("workflow") or payload.get("definition")
        if not isinstance(workflow, dict):
            return "Invalid payload: workflow must be a JSON object."
        await _write_workflow_path(session_id, path, workflow)
        return path

    return create_workflow


def create_read_workflow_tool(session_id: str) -> callable:
    @tool
    async def read_workflow(payload: dict) -> dict:
        """
        Read an existing workflow JSON file.

        Payload: { "path": "/workspace/workflow/xxx.json" }
        """
        path = _extract_path_from_payload(payload)
        if not path:
            return {"status": "error", "error": "Workflow path is required."}
        path = _normalize_workflow_path(path)
        try:
            workflow = await _read_workflow_file(session_id, path)
            return {"status": "success", "workflow": workflow, "path": path}
        except Exception as exc:
            return {"status": "error", "error": str(exc), "path": path}

    return read_workflow


def create_update_workflow_tool(session_id: str) -> callable:
    @tool
    async def update_workflow(payload: dict) -> str:
        """
        Update (overwrite) an existing workflow JSON file.

        Payload (structured frame):
        {
          "file_path": "/workspace/workflow/xxx.json",
          "workflow": { "root": { "nodes": {...}, "edges": {...} } }
        }
        """
        if not isinstance(payload, dict):
            return "Invalid payload: expected JSON object."
        path = _extract_path_from_payload(payload)
        if not path:
            return "Invalid payload: file_path is required."
        workflow = payload.get("workflow") or payload.get("definition")
        if not isinstance(workflow, dict):
            return "Invalid payload: workflow must be a JSON object."
        await _write_workflow_path(session_id, path, workflow)
        return path

    return update_workflow


def create_run_workflow_from_file_tool(session_id: str) -> callable:
    @tool
    async def run_workflow_from_file(payload: dict) -> dict:
        """
        Run a workflow JSON from the sandbox file system.

        Payload: { "path": "/workspace/workflow/xxx.json" }
        """
        path = _extract_path_from_payload(payload)
        if not path:
            return {"status": "error", "error": "Workflow path is required."}
        path = _normalize_workflow_path(path)
        db = SessionLocal()
        try:
            session = _get_session(db, session_id)
            if not session:
                return {"status": "error", "error": "Session not found."}
            result = await service_run_workflow_from_file(db, session.user_id, session_id, path)
            return result
        finally:
            db.close()

    return run_workflow_from_file


def create_design_workflow_tool(model, session_id: str, system_prompt: str, callbacks: list | None = None) -> callable:
    @tool
    async def design_workflow(goal: str) -> str:
        """
        Design a full workflow JSON, validate it, and summarize the outcome.
        """
        db = SessionLocal()
        try:
            session = _get_session(db, session_id)
            if not session:
                return "Session not found."
            workflow_agent = WorkflowAgent(
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
            result = await workflow_agent.ainvoke(
                goal,
                thread_id=f"workflow_agent_{session_id}",
                config={"callbacks": callbacks},
            )
            messages = result.get("messages", [])
            return messages[-1].content if messages else ""
        finally:
            db.close()

    return design_workflow
