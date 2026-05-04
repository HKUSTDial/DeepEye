from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Awaitable, Callable

from app.workflow.services.tracking import finalize_tracked_workflow_run, replace_workflow_artifacts
from deepeye.workflows.models import Graph
from deepeye.workflows.runtime import ExecutionContext

PublishWorkflowEvent = Callable[[str, dict[str, Any] | None], Awaitable[None]]


def timestamp_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def build_workflow_identity(
    session_id: str,
    workflow_ref: str | None,
    tracked_draft,
    workflow_path: str | None,
) -> str:
    if workflow_ref:
        return workflow_ref
    if tracked_draft:
        return f"draft:{tracked_draft.id}"
    if workflow_path:
        return f"file:{workflow_path}"
    return f"session:{session_id}"


def build_tracking_refs(tracked_turn, tracked_draft, tracked_run, fallback_turn_id: str | None) -> dict[str, str | None]:
    return {
        "turn_id": str(tracked_turn.id) if tracked_turn else fallback_turn_id,
        "draft_id": str(tracked_draft.id) if tracked_draft else None,
        "run_id": str(tracked_run.id) if tracked_run else None,
    }


def summarize_failed_context(graph: Graph, context: ExecutionContext) -> tuple[str, list[dict[str, Any]]]:
    failed_nodes: list[dict[str, Any]] = []
    for node_id, node_run in context.runs.items():
        if node_run.status != "failed":
            continue
        node = graph.nodes.get(node_id)
        failed_nodes.append(
            {
                "node_id": node_id,
                "node_type": node.type if node else None,
                "message": node_run.error or "Node execution failed.",
            }
        )

    if not failed_nodes:
        return "Workflow execution failed.", []

    first = failed_nodes[0]
    node_label = first.get("node_id") or "unknown"
    node_type = first.get("node_type")
    message = first.get("message") or "Node execution failed."
    if node_type:
        summary = f"Workflow execution failed at node {node_label} ({node_type}): {message}"
    else:
        summary = f"Workflow execution failed at node {node_label}: {message}"
    return summary, failed_nodes


def collect_final_outputs(graph: Graph, context: ExecutionContext) -> dict[str, Any]:
    outputs: dict[str, Any] = {}
    for node_id in graph.nodes.keys():
        run = context.runs.get(node_id)
        if not run or not run.outputs:
            continue
        non_empty = {key: value for key, value in run.outputs.items() if value not in (None, "", [], {})}
        if non_empty:
            outputs[node_id] = non_empty
    return outputs


async def finalize_failed_run(
    db,
    tracked_run,
    publish_workflow_event: PublishWorkflowEvent,
    *,
    error: str,
    result: dict[str, Any],
    error_payload: dict[str, Any],
    run_end_payload: dict[str, Any],
) -> None:
    if tracked_run:
        finalize_tracked_workflow_run(
            db,
            tracked_run,
            status="failed",
            result=result,
            error=error,
            artifacts=[],
        )
    await publish_workflow_event("error", error_payload)
    await publish_workflow_event("run_end", run_end_payload)


async def finalize_successful_run(
    db,
    tracked_run,
    publish_workflow_event: PublishWorkflowEvent,
    *,
    status: str,
    compact_outputs: dict[str, Any],
    artifacts: list[dict[str, Any]],
) -> None:
    if tracked_run:
        replace_workflow_artifacts(db, tracked_run, artifacts)
        finalize_tracked_workflow_run(
            db,
            tracked_run,
            status=status,
            result={"status": status, "outputs": compact_outputs, "artifacts": artifacts},
            artifacts=artifacts,
        )
    await publish_workflow_event(
        "run_end",
        {
            "status": status,
            "finished_at": timestamp_utc(),
            "outputs": compact_outputs,
            "artifacts": artifacts,
        },
    )
