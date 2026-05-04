from __future__ import annotations

from typing import Any

from app.workflow.services.tracking import build_workspace_state, build_workspace_state_for_turn
from app.workflow.repair.state import _terminal_failure_reply
from app.workflow.services.workspace_state import extract_final_answer, serialize_workspace_state
from deepeye.utils.logger import logger


def serialize_workflow_agent_workspace_state(
    db,
    *,
    session_id: str,
    turn_id: str | None = None,
) -> dict[str, Any]:
    try:
        snapshot = build_workspace_state_for_turn(db, turn_id) if turn_id else build_workspace_state(db, session_id)
    except Exception as exc:
        logger.warning("[workflow_agent_response] failed to build workspace state: %s", exc)
        return {}
    return serialize_workspace_state(snapshot) if snapshot else {}


def build_workflow_agent_response(
    *,
    goal: str,
    agent_result: dict[str, Any],
    turn_id: str | None,
    terminal_failure: dict[str, Any] | None,
    workspace_state: dict[str, Any],
) -> dict[str, Any]:
    run = workspace_state.get("run") or {}
    run_result = run.get("result") or {}
    run_status = run.get("status") or "pending"
    final_answer = extract_final_answer(workspace_state)
    artifacts = [artifact.get("kind") for artifact in workspace_state.get("artifacts", [])]
    message_count = len(agent_result.get("messages", []))

    if terminal_failure:
        return {
            "status": "failed",
            "next_action": "reply_directly",
            "turn_id": turn_id,
            "draft_id": terminal_failure.get("draft_id") or (workspace_state.get("draft") or {}).get("id"),
            "run_id": terminal_failure.get("run_id") or run.get("id"),
            "run_status": "failed",
            "error": terminal_failure.get("error"),
            "error_type": terminal_failure.get("error_type"),
            "error_summary": terminal_failure.get("error_summary"),
            "issues": terminal_failure.get("issues") or [],
            "validation_errors": terminal_failure.get("validation_errors"),
            "details": terminal_failure.get("details"),
            "artifacts": artifacts,
            "workspace_state": workspace_state,
            "final_answer": _terminal_failure_reply(goal, terminal_failure),
            "message_count": message_count,
        }

    return {
        "status": "success" if run_status == "success" else run_status,
        "next_action": "reply_directly" if final_answer and run_status == "success" else "summarize_workflow_result",
        "turn_id": turn_id,
        "draft_id": (workspace_state.get("draft") or {}).get("id"),
        "run_id": run.get("id"),
        "run_status": run_status,
        "error": run.get("error"),
        "validation_errors": run_result.get("validation_errors"),
        "details": run_result.get("details"),
        "artifacts": artifacts,
        "workspace_state": workspace_state,
        "final_answer": final_answer,
        "message_count": message_count,
    }
