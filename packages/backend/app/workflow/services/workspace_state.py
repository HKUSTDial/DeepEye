from __future__ import annotations

from copy import deepcopy

from app.workflow.services.datasets import compact_value_for_transport, compact_workflow_result


_SUMMARY_ARTIFACT_REFERENCE_KEYS = (
    "dashboard_url",
    "report_path",
    "video_url",
    "video_path",
    "task_id",
    "output_path",
)


def serialize_workspace_state(snapshot: dict) -> dict:
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


def dedupe_summary_artifact_references(workspace_state: dict | None) -> dict:
    if not isinstance(workspace_state, dict):
        return {}

    deduped = deepcopy(workspace_state)
    artifacts = deduped.get("artifacts")
    if not isinstance(artifacts, list):
        return deduped

    seen_references: dict[str, set[str]] = {}
    for artifact in artifacts:
        if not isinstance(artifact, dict):
            continue
        payload = artifact.get("payload")
        if not isinstance(payload, dict):
            continue
        for key in _SUMMARY_ARTIFACT_REFERENCE_KEYS:
            value = payload.get(key)
            if isinstance(value, str) and value.strip():
                seen_references.setdefault(key, set()).add(value.strip())

    run = deduped.get("run")
    if not isinstance(run, dict):
        return deduped
    result = run.get("result")
    if not isinstance(result, dict):
        return deduped
    outputs = result.get("outputs")
    if not isinstance(outputs, dict):
        return deduped

    for node_output in outputs.values():
        if not isinstance(node_output, dict):
            continue
        for key, values in seen_references.items():
            value = node_output.get(key)
            if isinstance(value, str) and value.strip() in values:
                node_output.pop(key, None)

    return deduped


def extract_final_answer(workspace_state: dict | None) -> str | None:
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
