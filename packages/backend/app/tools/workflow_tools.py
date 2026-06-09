from __future__ import annotations

from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from app.db.session import SessionLocal
from app.agent.prompts import build_workflow_summary_prompt
from app.workflow.services.agent_drafts import read_workflow_definition, save_agent_workflow_draft
from app.workflow.services.agent_response import (
    build_workflow_agent_response,
    serialize_workflow_agent_workspace_state,
)
from app.workflow.services.agent_runs import (
    WorkflowAgentRunOutcome,
    create_and_run_agent_workflow_draft,
    get_workflow_session,
    run_agent_workflow_draft,
    run_agent_workflow_file,
)
from app.workflow.services.tracking import build_workspace_state, build_workspace_state_for_turn
from app.workflow.repair.state import (
    _build_tool_failure,
    _guard_repair_limit,
    _mark_terminal_failure,
    _new_repair_state,
    _normalize_workflow_run_result,
    _note_successful_run,
    _register_repairable_failure,
    _repair_limit_failure,
    _require_reuse_after_failure,
)
from app.workflow.services.workspace_state import (
    dedupe_summary_artifact_references,
    extract_final_answer,
    serialize_workspace_state,
)
from app.tools.workflow.payloads import _normalize_workflow_payload_shape
from deepeye.agents import WorkflowAgent
from deepeye.tools.base import tool


def _empty_to_none(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip()
    return value or None


def _build_run_failure_response(
    outcome: WorkflowAgentRunOutcome,
    repair_state: dict[str, Any] | None,
) -> dict:
    failure = _build_tool_failure(
        draft_id=outcome.draft_id,
        error_type=outcome.error_type or "workflow_run_failed",
        error_summary=outcome.error_summary or outcome.error or "Workflow run failed.",
        repairable=outcome.repairable,
        error=outcome.error or "Workflow run failed.",
    )
    if repair_state:
        return _mark_terminal_failure(repair_state, failure)
    return failure


def _finalize_workflow_run_result(
    normalized: dict,
    repair_state: dict[str, Any] | None,
    draft_id: str,
) -> dict:
    if repair_state:
        if normalized["status"] == "success":
            _note_successful_run(repair_state, draft_id)
        elif normalized["repairable"]:
            limit_failure = _register_repairable_failure(repair_state, draft_id)
            if limit_failure:
                return limit_failure
            if repair_state.get("limit_exhausted"):
                return _repair_limit_failure(repair_state, normalized)
        else:
            return _mark_terminal_failure(repair_state, normalized)
    return normalized


def create_create_workflow_tool(session_id: str, user_id: str, turn_id: str | None = None) -> callable:
    @tool
    async def create_workflow(
        workflow: dict,
        draft_id: str = "",
        name: str = "",
        file_path: str = "",
        planning_notes: str = "",
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
        saved = await save_agent_workflow_draft(
            session_id=session_id,
            user_id=user_id,
            definition=workflow,
            turn_id=turn_id,
            draft_id=_empty_to_none(draft_id),
            file_path=_empty_to_none(file_path),
            name=_empty_to_none(name),
        )
        return {"status": "success", "draft_id": saved.draft_id}

    return create_workflow


def create_read_workflow_tool(session_id: str) -> callable:
    @tool
    async def read_workflow(draft_id: str = "", file_path: str = "") -> dict:
        """
        Read an existing workflow draft.

        Args:
            draft_id: Workflow draft id. Preferred.
            file_path: Explicit legacy sandbox workflow JSON file path. Fallback only.
        """
        result = await read_workflow_definition(
            session_id=session_id,
            draft_id=_empty_to_none(draft_id),
            file_path=_empty_to_none(file_path),
        )
        return result.to_tool_response()

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
        draft_id: str = "",
        name: str = "",
        file_path: str = "",
        planning_notes: str = "",
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
            reuse_failure = _require_reuse_after_failure(repair_state, _empty_to_none(draft_id))
            if reuse_failure:
                return reuse_failure
        workflow = _normalize_workflow_payload_shape(workflow)
        saved = await save_agent_workflow_draft(
            session_id=session_id,
            user_id=user_id,
            definition=workflow,
            turn_id=turn_id,
            draft_id=_empty_to_none(draft_id),
            file_path=_empty_to_none(file_path),
            name=_empty_to_none(name),
        )
        return {"status": "success", "draft_id": saved.draft_id}

    return update_workflow


def create_run_workflow_from_file_tool(session_id: str, turn_id: str | None = None) -> callable:
    @tool
    async def run_workflow_from_file(file_path: str) -> dict:
        """
        Run a workflow directly from a known sandbox file path.

        Args:
            file_path: Workflow JSON file path for an explicitly file-based workflow.
        """
        return await run_agent_workflow_file(session_id=session_id, file_path=file_path, turn_id=turn_id)

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
        outcome = await run_agent_workflow_draft(session_id=session_id, draft_id=draft_id, turn_id=turn_id)
        if outcome.is_failure:
            return _build_run_failure_response(outcome, repair_state)
        normalized = _normalize_workflow_run_result(
            outcome.raw_result or {},
            draft_id=outcome.draft_id or draft_id,
            workflow_definition=outcome.workflow_definition or {},
        )
        return _finalize_workflow_run_result(normalized, repair_state, outcome.draft_id or draft_id)

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
        draft_id: str = "",
        name: str = "",
        file_path: str = "",
        planning_notes: str = "",
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
            reuse_failure = _require_reuse_after_failure(repair_state, _empty_to_none(draft_id))
            if reuse_failure:
                return reuse_failure
        workflow = _normalize_workflow_payload_shape(workflow)
        outcome = await create_and_run_agent_workflow_draft(
            session_id=session_id,
            definition=workflow,
            turn_id=turn_id,
            draft_id=_empty_to_none(draft_id),
            file_path=_empty_to_none(file_path),
            name=_empty_to_none(name),
        )
        if outcome.is_failure:
            return _build_run_failure_response(outcome, repair_state)
        normalized = _normalize_workflow_run_result(
            outcome.raw_result or {},
            draft_id=outcome.draft_id or _empty_to_none(draft_id),
            workflow_definition=outcome.workflow_definition or workflow,
        )
        return _finalize_workflow_run_result(normalized, repair_state, outcome.draft_id or draft_id or "")

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
            session = get_workflow_session(db, session_id)
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
            serialized = serialize_workflow_agent_workspace_state(db, session_id=session_id, turn_id=turn_id)
            return build_workflow_agent_response(
                goal=goal,
                agent_result=result,
                turn_id=turn_id,
                terminal_failure=repair_state.get("terminal_failure"),
                workspace_state=serialized,
            )
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

        serialized = serialize_workspace_state(snapshot)
        run = serialized.get("run")
        if not run:
            return "No workflow run is available to summarize yet."
        final_answer = extract_final_answer(serialized)
        if final_answer:
            return final_answer

        prompt = build_workflow_summary_prompt(
            question,
            dedupe_summary_artifact_references(serialized),
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
