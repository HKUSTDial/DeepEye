from __future__ import annotations

import json
import uuid

from langchain_core.messages import HumanMessage, SystemMessage

from app.db.session import SessionLocal
from app.repositories import SessionRepository
from app.sandbox import sandbox_manager
from app.services.agent_prompts import build_workflow_summary_prompt
from app.services.workflow_datasets import compact_value_for_transport, compact_workflow_result
from app.services.workflow_file_service import (
    service_run_workflow_draft,
    service_run_workflow_from_file,
    write_workflow_definition_to_file,
)
from app.services.workflow_targets import normalize_workflow_path, save_workflow_draft, resolve_workflow_target
from app.services.workflow_tracking_service import build_workspace_state, build_workspace_state_for_turn
from deepeye.agents import WorkflowAgent
from deepeye.tools.base import tool
from deepeye.utils.logger import logger


def _get_session(db, session_id: str):
    try:
        session_uuid = uuid.UUID(session_id)
    except (TypeError, ValueError):
        logger.warning("[workflow_tools] Invalid session_id=%s", session_id)
        return None
    return SessionRepository(db).get(session_uuid)


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


def _serialize_workspace_state(snapshot: dict) -> dict:
    turn = snapshot.get("turn")
    draft = snapshot.get("draft")
    run = snapshot.get("run")
    artifacts = snapshot.get("artifacts") or []
    return {
        "session_id": str(snapshot.get("session_id")) if snapshot.get("session_id") is not None else None,
        "turn": (
            {
                "id": str(turn.id),
                "status": turn.status,
                "input_text": turn.input_text,
                "error": turn.error,
            }
            if turn
            else None
        ),
        "draft": (
            {
                "id": str(draft.id),
                "status": draft.status,
                "version": draft.version,
                "source": draft.source,
            }
            if draft
            else None
        ),
        "run": (
            {
                "id": str(run.id),
                "status": run.status,
                "error": run.error,
                "result": compact_workflow_result(run.result, row_limit=10, text_limit=2500),
            }
            if run
            else None
        ),
        "artifacts": [
            {
                "id": str(artifact.id),
                "kind": artifact.kind,
                "payload": compact_value_for_transport(artifact.payload, row_limit=10, text_limit=2500),
            }
            for artifact in artifacts
        ],
    }


def _extract_final_answer(workspace_state: dict | None) -> str | None:
    if not isinstance(workspace_state, dict):
        return None
    run = workspace_state.get("run")
    if not isinstance(run, dict):
        return None
    result = run.get("result")
    if not isinstance(result, dict):
        return None
    outputs = result.get("outputs")
    if not isinstance(outputs, dict):
        return None
    for node_output in outputs.values():
        if not isinstance(node_output, dict):
            continue
        answer = node_output.get("answer")
        if isinstance(answer, str) and answer.strip():
            return answer.strip()
    return None


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
    async def workflow_agent(goal: str) -> dict:
        """
        Workflow planner and executor.
        Use this for tasks that need workflow planning and execution.
        Returns structured execution metadata and may include a ready-to-send final_answer.
        """
        db = SessionLocal()
        try:
            session = _get_session(db, session_id)
            if not session:
                return {"status": "error", "error": "Session not found."}
            workflow_agent_inst = WorkflowAgent(
                model=model,
                system_prompt=system_prompt,
                tools=[
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
            try:
                snapshot = (
                    build_workspace_state_for_turn(db, turn_id)
                    if turn_id
                    else build_workspace_state(db, session_id)
                )
            except Exception as exc:
                logger.warning("[workflow_agent tool] failed to build workspace state: %s", exc)
                snapshot = None
            serialized = _serialize_workspace_state(snapshot) if snapshot else {}
            run = serialized.get("run") or {}
            run_result = run.get("result") or {}
            run_status = run.get("status") or "pending"
            final_answer = _extract_final_answer(serialized)
            return {
                "status": "success" if run_status == "success" else run_status,
                "next_action": "reply_directly" if final_answer and run_status == "success" else "summarize_workflow_result",
                "turn_id": turn_id,
                "draft_id": (serialized.get("draft") or {}).get("id"),
                "run_id": run.get("id"),
                "run_status": run_status,
                "error": run.get("error"),
                "validation_errors": run_result.get("validation_errors"),
                "details": run_result.get("details"),
                "artifacts": [artifact.get("kind") for artifact in serialized.get("artifacts", [])],
                "workspace_state": serialized,
                "final_answer": final_answer,
                "message_count": len(result.get("messages", [])),
            }
        finally:
            db.close()

    return workflow_agent


def create_summarize_workflow_result_tool(
    model,
    session_id: str,
    turn_id: str | None = None,
) -> callable:
    @tool
    async def summarize_workflow_result(question: str) -> str:
        """
        Summarize the latest workflow run for the current user request.
        Always use this after workflow_agent before replying to the user.
        """
        db = SessionLocal()
        try:
            snapshot = (
                build_workspace_state_for_turn(db, turn_id)
                if turn_id
                else build_workspace_state(db, session_id)
            )
        finally:
            db.close()

        serialized = _serialize_workspace_state(snapshot)
        run = serialized.get("run")
        if not run:
            return "No workflow run is available to summarize yet."
        final_answer = _extract_final_answer(serialized)
        if final_answer:
            return final_answer

        prompt = build_workflow_summary_prompt(question, serialized)
        response = await model.ainvoke(
            [
                SystemMessage(content=prompt),
                HumanMessage(content=question),
            ]
        )
        content = getattr(response, "content", "")
        return content if isinstance(content, str) else str(content)

    return summarize_workflow_result
