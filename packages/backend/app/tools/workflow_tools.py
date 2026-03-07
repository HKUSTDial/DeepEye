from __future__ import annotations

import json
import uuid
from typing import Annotated, List

from langchain_core.messages import ToolMessage
from langchain_core.tools import InjectedToolCallId
from langgraph.types import Command

from app.db.session import SessionLocal
from app.repositories import SessionRepository
from app.sandbox import sandbox_manager
from app.services.workflow_file_service import (
    service_run_workflow_draft,
    service_run_workflow_from_file,
    write_workflow_definition_to_file,
)
from app.services.workflow_targets import normalize_workflow_path, save_workflow_draft, resolve_workflow_target
from deepeye.agents import WorkflowAgent
from deepeye.tools.base import tool
from deepeye.tools.planning_tools import mark_step_done, update_plan
from deepeye.utils.logger import logger


def _get_session(db, session_id: str):
    try:
        session_uuid = uuid.UUID(session_id)
    except (TypeError, ValueError):
        logger.warning("[workflow_tools] Invalid session_id=%s", session_id)
        return None
    return SessionRepository(db).get(session_uuid)


@tool
def create_plan(
    steps: List[str],
    tool_call_id: Annotated[str, InjectedToolCallId],
) -> Annotated[Command, "The result of creating the plan"]:
    """Create a new execution plan with a list of steps. After this you MUST create/update a workflow draft and run it before replying."""
    return Command(
        update={
            "plan": steps,
            "completed_steps": [],
            "messages": [
                ToolMessage(
                    content=(
                        "Plan created. Next you MUST call create_workflow_and_run with workflow and an optional name, "
                        "or create_workflow followed by run_workflow. Reuse the returned draft_id for follow-up steps. "
                        "Use file_path only for an explicit legacy sandbox workflow file. "
                        "Do not reply until a workflow run has returned."
                    ),
                    tool_call_id=tool_call_id,
                )
            ],
        }
    )


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


def create_create_workflow_tool(session_id: str, user_id: str, turn_id: str | None = None) -> callable:
    @tool
    async def create_workflow(
        workflow: dict,
        draft_id: str | None = None,
        name: str | None = None,
        file_path: str | None = None,
    ) -> dict:
        """
        Create a workflow draft or replace an existing draft.

        Args:
            workflow: The full workflow definition object.
            draft_id: Existing workflow draft id to update.
            name: Optional logical workflow name. Used to derive file path if needed.
            file_path: Optional explicit legacy sandbox workflow file path. Prefer draft_id or name.
        """
        db = SessionLocal()
        try:
            draft = save_workflow_draft(
                db,
                session_id=session_id,
                user_id=user_id,
                definition=workflow,
                turn_id=turn_id,
                draft_id=draft_id,
                file_path=file_path,
                name=name,
                source="workflow_agent",
            )
        finally:
            db.close()

        norm_path = draft.file_path or normalize_workflow_path(file_path or name or "workflow.json")
        await write_workflow_definition_to_file(session_id, norm_path, workflow)
        return {"status": "success", "draft_id": str(draft.id)}

    return create_workflow


def create_read_workflow_tool(session_id: str) -> callable:
    @tool
    async def read_workflow(draft_id: str | None = None, file_path: str | None = None) -> dict:
        """
        Read an existing workflow draft.

        Args:
            draft_id: Workflow draft id. Preferred.
            file_path: Explicit legacy sandbox workflow JSON file path. Fallback only.
        """
        if not draft_id and not file_path:
            return {"status": "error", "error": "Provide draft_id. Use file_path only for an explicit legacy workflow file."}

        db = SessionLocal()
        try:
            existing_draft, norm_path = resolve_workflow_target(
                db,
                session_id,
                draft_id=draft_id,
                file_path=file_path,
            )
            if existing_draft and isinstance(existing_draft.definition, dict) and existing_draft.definition:
                return {
                    "status": "success",
                    "workflow": existing_draft.definition,
                    "draft_id": str(existing_draft.id),
                }
        finally:
            db.close()

        try:
            workflow = await _read_workflow_file(session_id, norm_path)
            return {"status": "success", "workflow": workflow, "draft_id": draft_id}
        except Exception as exc:
            return {"status": "error", "error": str(exc), "draft_id": draft_id}

    return read_workflow


def create_update_workflow_tool(session_id: str, user_id: str, turn_id: str | None = None) -> callable:
    @tool
    async def update_workflow(
        workflow: dict,
        draft_id: str | None = None,
        name: str | None = None,
        file_path: str | None = None,
    ) -> dict:
        """
        Update an existing workflow draft or overwrite a file-backed workflow.

        Args:
            workflow: The full workflow definition object.
            draft_id: Existing workflow draft id to update.
            name: Optional logical workflow name. Used to derive file path if needed.
            file_path: Optional explicit legacy sandbox workflow file path. Prefer draft_id.
        """
        db = SessionLocal()
        try:
            draft = save_workflow_draft(
                db,
                session_id=session_id,
                user_id=user_id,
                definition=workflow,
                turn_id=turn_id,
                draft_id=draft_id,
                file_path=file_path,
                name=name,
                source="workflow_agent",
            )
        finally:
            db.close()

        norm_path = draft.file_path or normalize_workflow_path(file_path or name or "workflow.json")
        await write_workflow_definition_to_file(session_id, norm_path, workflow)
        return {"status": "success", "draft_id": str(draft.id)}

    return update_workflow


def create_run_workflow_from_file_tool(session_id: str, turn_id: str | None = None) -> callable:
    @tool
    async def run_workflow_from_file(file_path: str) -> dict:
        """
        Run a workflow directly from a known sandbox file path.

        Args:
            file_path: Workflow JSON file path for an explicitly file-based workflow.
        """
        db = SessionLocal()
        try:
            session = _get_session(db, session_id)
            if not session:
                return {"status": "error", "error": "Session not found."}
            _, norm_path = resolve_workflow_target(
                db,
                session_id,
                file_path=file_path,
            )
            return await service_run_workflow_from_file(
                db,
                session.user_id,
                session_id,
                norm_path,
                turn_id=turn_id,
            )
        finally:
            db.close()

    return run_workflow_from_file


def create_run_workflow_tool(session_id: str, turn_id: str | None = None) -> callable:
    @tool
    async def run_workflow(draft_id: str) -> dict:
        """
        Run a workflow draft by id.

        Args:
            draft_id: Workflow draft id to execute.
        """
        db = SessionLocal()
        try:
            session = _get_session(db, session_id)
            if not session:
                return {"status": "error", "error": "Session not found."}
            existing_draft, norm_path = resolve_workflow_target(
                db,
                session_id,
                draft_id=draft_id,
            )
            if not existing_draft or not isinstance(existing_draft.definition, dict):
                return {"status": "error", "error": "Workflow draft not found."}
            return await service_run_workflow_draft(
                db,
                session.user_id,
                session_id,
                str(existing_draft.id),
                turn_id=turn_id,
            )
        finally:
            db.close()

    return run_workflow


def create_workflow_and_run_tool(session_id: str, turn_id: str | None = None) -> callable:
    """Single tool: create/update a workflow draft and run it immediately."""

    @tool
    async def create_workflow_and_run(
        workflow: dict,
        draft_id: str | None = None,
        name: str | None = None,
        file_path: str | None = None,
    ) -> dict:
        """
        Create or update a workflow draft and run it immediately.

        Args:
            workflow: Full workflow with root.nodes and root.edges.
            draft_id: Existing workflow draft id to update and execute.
            name: Optional logical workflow name. Used to derive file path if needed.
            file_path: Optional explicit legacy sandbox workflow file path. Prefer name or draft_id.
        """
        db = SessionLocal()
        try:
            session = _get_session(db, session_id)
            if not session:
                return {"status": "error", "error": "Session not found."}
            draft = save_workflow_draft(
                db,
                session_id=session_id,
                user_id=str(session.user_id),
                definition=workflow,
                turn_id=turn_id,
                draft_id=draft_id,
                file_path=file_path,
                name=name,
                source="workflow_agent",
            )
            result = await service_run_workflow_draft(
                db,
                session.user_id,
                session_id,
                str(draft.id),
                turn_id=turn_id,
            )
            return {"status": "success", "draft_id": str(draft.id), "run": result}
        finally:
            db.close()

    return create_workflow_and_run


def create_design_workflow_tool(
    model,
    session_id: str,
    system_prompt: str,
    callbacks: list | None = None,
    turn_id: str | None = None,
) -> callable:
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
                    create_workflow_and_run_tool(session_id, turn_id=turn_id),
                    create_create_workflow_tool(session_id, str(session.user_id), turn_id=turn_id),
                    create_read_workflow_tool(session_id),
                    create_update_workflow_tool(session_id, str(session.user_id), turn_id=turn_id),
                    create_run_workflow_tool(session_id, turn_id=turn_id),
                    create_run_workflow_from_file_tool(session_id, turn_id=turn_id),
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
