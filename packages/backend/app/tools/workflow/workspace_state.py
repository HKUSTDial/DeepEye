from __future__ import annotations

from typing import Any

from app.services.workflow_datasets import compact_value_for_transport, compact_workflow_result


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
