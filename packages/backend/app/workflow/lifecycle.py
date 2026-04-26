"""Workflow run lifecycle helpers."""

from __future__ import annotations

from typing import Literal, cast

WorkflowRunStatus = Literal["queued", "running", "success", "failed", "completed", "cancelled"]

_WORKFLOW_RUN_STATUS_ALIASES: dict[str, WorkflowRunStatus] = {
    "created": "queued",
    "pending": "queued",
    "queued": "queued",
    "running": "running",
    "started": "running",
    "ok": "success",
    "ready": "success",
    "succeeded": "success",
    "success": "success",
    "complete": "completed",
    "completed": "completed",
    "done": "completed",
    "error": "failed",
    "errored": "failed",
    "failed": "failed",
    "failure": "failed",
    "cancelled": "cancelled",
    "canceled": "cancelled",
}

FINAL_WORKFLOW_RUN_STATUSES: frozenset[WorkflowRunStatus] = frozenset(
    {"success", "failed", "completed", "cancelled"}
)
_SUCCESSFUL_WORKFLOW_RUN_STATUSES: frozenset[WorkflowRunStatus] = frozenset({"success", "completed"})


def normalize_workflow_run_status(status: str | None) -> WorkflowRunStatus:
    """Normalize legacy run status aliases to the canonical lifecycle vocabulary."""
    if not status:
        return "running"
    return cast(WorkflowRunStatus, _WORKFLOW_RUN_STATUS_ALIASES.get(status.strip().lower(), "running"))


def next_turn_status_after_run_finalized(
    run_status: str | None,
    current_turn_status: str | None,
) -> str | None:
    """Return the chat turn status transition triggered by a finalized workflow run."""
    if current_turn_status == "failed":
        return None
    if normalize_workflow_run_status(run_status) in _SUCCESSFUL_WORKFLOW_RUN_STATUSES:
        return "summarizing"
    return None
