from __future__ import annotations

import json
import shlex
import uuid
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from app.db.session import SessionLocal
from app.repositories import SessionRepository
from app.sandbox import sandbox_manager
from app.services.agent_prompts import build_workflow_summary_prompt
from app.services.workflow_file_service import (
    service_run_workflow_draft,
    service_run_workflow_from_file,
    write_workflow_definition_to_file,
)
from app.services.workflow_targets import normalize_workflow_path, save_workflow_draft, resolve_workflow_target
from app.services.workflow_tracking_service import build_workspace_state, build_workspace_state_for_turn
from app.tools.workflow.payloads import _normalize_workflow_payload_shape
from app.tools.workflow.repairs import (
    _build_tool_failure,
    _guard_repair_limit,
    _mark_terminal_failure,
    _new_repair_state,
    _normalize_workflow_run_result,
    _note_successful_run,
    _register_repairable_failure,
    _repair_limit_failure,
    _require_reuse_after_failure,
    _terminal_failure_reply,
)
from app.tools.workflow.workspace_state import (
    _dedupe_summary_artifact_references,
    _extract_final_answer,
    _serialize_workspace_state,
)
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
    result = await sandbox.exec_command(f"cat {shlex.quote(path)}")
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
        planning_notes: str | None = None,
    ) -> dict:
        """
        Create a workflow draft or replace an existing draft.

        Args:
            workflow: The full workflow definition object.
            draft_id: Existing workflow draft id to update.
            name: Optional logical workflow name. Used to derive file path if needed.
            file_path: Optional explicit legacy sandbox workflow file path. Prefer draft_id or name.
            planning_notes: Concise step-by-step planning notes explaining nodes, schemas, and edges.
        """
        workflow = _normalize_workflow_payload_shape(workflow)
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


def create_update_workflow_tool(
    session_id: str,
    user_id: str,
    turn_id: str | None = None,
    repair_state: dict[str, Any] | None = None,
) -> callable:
    @tool
    async def update_workflow(
        workflow: dict,
        draft_id: str | None = None,
        name: str | None = None,
        file_path: str | None = None,
        planning_notes: str | None = None,
    ) -> dict:
        """
        Update an existing workflow draft or overwrite a file-backed workflow.

        Args:
            workflow: The full workflow definition object.
            draft_id: Existing workflow draft id to update.
            name: Optional logical workflow name. Used to derive file path if needed.
            file_path: Optional explicit legacy sandbox workflow file path. Prefer draft_id.
            planning_notes: Concise step-by-step planning notes explaining nodes, schemas, and edges.
        """
        if repair_state:
            blocked = _guard_repair_limit(repair_state)
            if blocked:
                return blocked
            reuse_failure = _require_reuse_after_failure(repair_state, draft_id)
            if reuse_failure:
                return reuse_failure
        workflow = _normalize_workflow_payload_shape(workflow)
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


def create_run_workflow_tool(
    session_id: str,
    turn_id: str | None = None,
    repair_state: dict[str, Any] | None = None,
) -> callable:
    @tool
    async def run_workflow(draft_id: str) -> dict:
        """
        Run a workflow draft by id.

        Args:
            draft_id: Workflow draft id to execute.
        """
        if repair_state:
            blocked = _guard_repair_limit(repair_state)
            if blocked:
                return blocked
            reuse_failure = _require_reuse_after_failure(repair_state, draft_id)
            if reuse_failure:
                return reuse_failure
        db = SessionLocal()
        try:
            session = _get_session(db, session_id)
            if not session:
                failure = _build_tool_failure(
                    draft_id=draft_id,
                    error_type="session_not_found",
                    error_summary="Session not found.",
                    repairable=False,
                    error="Session not found.",
                )
                if repair_state:
                    return _mark_terminal_failure(repair_state, failure)
                return failure
            existing_draft, norm_path = resolve_workflow_target(
                db,
                session_id,
                draft_id=draft_id,
            )
            if not existing_draft or not isinstance(existing_draft.definition, dict):
                failure = _build_tool_failure(
                    draft_id=draft_id,
                    error_type="draft_not_found",
                    error_summary="Workflow draft not found.",
                    repairable=False,
                    error="Workflow draft not found.",
                )
                if repair_state:
                    return _mark_terminal_failure(repair_state, failure)
                return failure
            result = await service_run_workflow_draft(
                db,
                session.user_id,
                session_id,
                str(existing_draft.id),
                turn_id=turn_id,
            )
            normalized = _normalize_workflow_run_result(
                result,
                draft_id=str(existing_draft.id),
                workflow_definition=existing_draft.definition,
            )
            if repair_state:
                if normalized["status"] == "success":
                    _note_successful_run(repair_state, str(existing_draft.id))
                elif normalized["repairable"]:
                    limit_failure = _register_repairable_failure(repair_state, str(existing_draft.id))
                    if limit_failure:
                        return limit_failure
                    if repair_state.get("limit_exhausted"):
                        return _repair_limit_failure(repair_state, normalized)
                else:
                    return _mark_terminal_failure(repair_state, normalized)
            return normalized
        finally:
            db.close()

    return run_workflow


def create_workflow_and_run_tool(
    session_id: str,
    turn_id: str | None = None,
    repair_state: dict[str, Any] | None = None,
) -> callable:
    """Single tool: create/update a workflow draft and run it immediately."""

    @tool
    async def create_workflow_and_run(
        workflow: dict,
        draft_id: str | None = None,
        name: str | None = None,
        file_path: str | None = None,
        planning_notes: str | None = None,
    ) -> dict:
        """
        Create or update a workflow draft and run it immediately.

        Args:
            workflow: Full workflow with root.nodes and root.edges.
            draft_id: Existing workflow draft id to update and execute.
            name: Optional logical workflow name. Used to derive file path if needed.
            file_path: Optional explicit legacy sandbox workflow file path. Prefer name or draft_id.
            planning_notes: Concise step-by-step planning notes explaining nodes, schemas, and edges.
        """
        if repair_state:
            blocked = _guard_repair_limit(repair_state)
            if blocked:
                return blocked
            reuse_failure = _require_reuse_after_failure(repair_state, draft_id)
            if reuse_failure:
                return reuse_failure
        workflow = _normalize_workflow_payload_shape(workflow)
        db = SessionLocal()
        try:
            session = _get_session(db, session_id)
            if not session:
                failure = _build_tool_failure(
                    draft_id=draft_id,
                    error_type="session_not_found",
                    error_summary="Session not found.",
                    repairable=False,
                    error="Session not found.",
                )
                if repair_state:
                    return _mark_terminal_failure(repair_state, failure)
                return failure
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
            normalized = _normalize_workflow_run_result(
                result,
                draft_id=str(draft.id),
                workflow_definition=workflow,
            )
            if repair_state:
                if normalized["status"] == "success":
                    _note_successful_run(repair_state, str(draft.id))
                elif normalized["repairable"]:
                    limit_failure = _register_repairable_failure(repair_state, str(draft.id))
                    if limit_failure:
                        return limit_failure
                    if repair_state.get("limit_exhausted"):
                        return _repair_limit_failure(repair_state, normalized)
                else:
                    return _mark_terminal_failure(repair_state, normalized)
            return normalized
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
            repair_state = _new_repair_state()
            workflow_agent_inst = WorkflowAgent(
                model=model,
                system_prompt=system_prompt,
                tools=[
                    create_workflow_and_run_tool(session_id, turn_id=turn_id, repair_state=repair_state),
                    create_read_workflow_tool(session_id),
                    create_update_workflow_tool(
                        session_id,
                        str(session.user_id),
                        turn_id=turn_id,
                        repair_state=repair_state,
                    ),
                    create_run_workflow_tool(session_id, turn_id=turn_id, repair_state=repair_state),
                ],
                max_steps=24,
                stop_condition=lambda: repair_state.get("terminal_failure"),
            )
            result = await workflow_agent_inst.ainvoke(
                goal,
                thread_id=f"workflow_agent_{session_id}",
                config={"callbacks": callbacks},
            )
            terminal_failure = repair_state.get("terminal_failure")
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
            if terminal_failure:
                return {
                    "status": "failed",
                    "next_action": "reply_directly",
                    "turn_id": turn_id,
                    "draft_id": terminal_failure.get("draft_id") or (serialized.get("draft") or {}).get("id"),
                    "run_id": terminal_failure.get("run_id") or run.get("id"),
                    "run_status": "failed",
                    "error": terminal_failure.get("error"),
                    "error_type": terminal_failure.get("error_type"),
                    "error_summary": terminal_failure.get("error_summary"),
                    "issues": terminal_failure.get("issues") or [],
                    "validation_errors": terminal_failure.get("validation_errors"),
                    "details": terminal_failure.get("details"),
                    "artifacts": [artifact.get("kind") for artifact in serialized.get("artifacts", [])],
                    "workspace_state": serialized,
                    "final_answer": _terminal_failure_reply(goal, terminal_failure),
                    "message_count": len(result.get("messages", [])),
                }
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

        prompt = build_workflow_summary_prompt(
            question,
            _dedupe_summary_artifact_references(serialized),
        )
        response = await model.ainvoke(
            [
                SystemMessage(content=prompt),
                HumanMessage(content=question),
            ],
            config={"tags": ["sub_agent"]},
        )
        content = getattr(response, "content", "")
        return content if isinstance(content, str) else str(content)

    return summarize_workflow_result
