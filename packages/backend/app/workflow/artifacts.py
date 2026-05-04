"""Workflow artifact normalization helpers.

The persisted artifact payload is intentionally backward-compatible: legacy
kind-specific fields stay at the top level while normalized preview metadata is
added alongside them.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from typing import Any

from app.schemas.workflow_artifact import WorkflowArtifactPayload

ARTIFACT_STATUS_ALIASES = {
    "complete": "ready",
    "completed": "ready",
    "done": "ready",
    "ok": "ready",
    "ready": "ready",
    "success": "ready",
    "succeeded": "ready",
    "error": "failed",
    "errored": "failed",
    "failed": "failed",
    "failure": "failed",
    "pending": "pending",
    "queued": "pending",
    "running": "running",
    "expired": "expired",
}

NORMALIZED_ARTIFACT_KEYS = {
    "files",
    "kind",
    "node_id",
    "payload",
    "preview",
    "status",
    "summary",
    "title",
}


def _is_empty(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return value.strip() == ""
    if isinstance(value, (Mapping, list, tuple, set)):
        return len(value) == 0
    return False


def _clean_mapping(fields: Mapping[str, Any] | None) -> dict[str, Any]:
    if not fields:
        return {}
    return {str(key): value for key, value in fields.items() if not _is_empty(value)}


def _clean_kind(kind: Any) -> str:
    if isinstance(kind, str) and kind.strip():
        return kind.strip().lower()
    return "artifact"


def _normalize_status(status: Any, fields: Mapping[str, Any], kind: str) -> str:
    if isinstance(status, str):
        normalized = ARTIFACT_STATUS_ALIASES.get(status.strip().lower())
        if normalized:
            return normalized

    if not _is_empty(fields.get("error")):
        return "failed"

    has_ready_preview = any(
        not _is_empty(fields.get(key))
        for key in (
            "dashboard_url",
            "report_html",
            "report_path",
            "video_path",
            "video_url",
        )
    )
    if has_ready_preview:
        return "ready"
    if kind in {"dataset", "table"} and (
        not _is_empty(fields.get("preview_rows")) or not _is_empty(fields.get("rows"))
    ):
        return "ready"
    if kind == "file" and not _is_empty(fields.get("file_path") or fields.get("path")):
        return "ready"
    if kind == "video" and not _is_empty(fields.get("task_id")):
        return "running"
    return "pending"


def _basename(path: Any) -> str | None:
    if not isinstance(path, str) or not path.strip():
        return None
    return os.path.basename(path.rstrip("/")) or path


def _file_descriptor(
    path: Any,
    *,
    role: str,
    mime_type: str | None = None,
    name: str | None = None,
) -> dict[str, Any] | None:
    if not isinstance(path, str) or not path.strip():
        return None
    descriptor: dict[str, Any] = {
        "name": name or _basename(path) or path,
        "path": path,
        "role": role,
    }
    if mime_type:
        descriptor["mime_type"] = mime_type
    return descriptor


def _merge_file_descriptors(
    existing: Any,
    derived: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    files: list[dict[str, Any]] = []
    if isinstance(existing, list):
        files.extend(item for item in existing if isinstance(item, dict))
    files.extend(derived)

    deduped: list[dict[str, Any]] = []
    seen: set[tuple[str | None, str | None]] = set()
    for file_info in files:
        key = (
            str(file_info.get("path")) if file_info.get("path") else None,
            str(file_info.get("url")) if file_info.get("url") else None,
        )
        if key == (None, None):
            deduped.append(file_info)
            continue
        if key in seen:
            continue
        seen.add(key)
        deduped.append(file_info)
    return deduped


def _derive_files(kind: str, fields: Mapping[str, Any]) -> list[dict[str, Any]]:
    files: list[dict[str, Any]] = []
    report_file = _file_descriptor(
        fields.get("report_path"),
        role="report",
        mime_type="text/html",
        name=str(fields.get("report_filename")) if isinstance(fields.get("report_filename"), str) else None,
    )
    if report_file:
        files.append(report_file)

    dashboard_source = _file_descriptor(fields.get("output_path"), role="source")
    if kind == "dashboard" and dashboard_source:
        files.append(dashboard_source)

    video_file = _file_descriptor(fields.get("video_path"), role="video", mime_type="video/mp4")
    if video_file:
        files.append(video_file)

    generic_file = _file_descriptor(fields.get("file_path") or fields.get("path"), role=kind)
    if kind in {"dataset", "file"} and generic_file:
        files.append(generic_file)

    return files


def _table_columns(fields: Mapping[str, Any], rows: list[Any]) -> list[str]:
    columns = fields.get("columns")
    if isinstance(columns, list):
        return [str(column) for column in columns if str(column).strip()]
    inferred = sorted({key for row in rows if isinstance(row, dict) for key in row})
    return inferred


def _derive_preview(kind: str, fields: Mapping[str, Any]) -> dict[str, Any]:
    existing = fields.get("preview")
    if isinstance(existing, dict) and isinstance(existing.get("type"), str):
        return dict(existing)

    if kind == "report":
        if not _is_empty(fields.get("report_html")):
            preview = {
                "content_key": "report_html",
                "mime_type": "text/html",
                "type": "html",
            }
            if not _is_empty(fields.get("report_path")):
                preview["path"] = fields["report_path"]
            return preview
        if not _is_empty(fields.get("report_path")):
            return {
                "mime_type": "text/html",
                "path": fields["report_path"],
                "type": "file",
            }

    if kind == "dashboard" and not _is_empty(fields.get("dashboard_url")):
        return {"type": "url", "url": fields["dashboard_url"]}

    if kind == "video":
        if not _is_empty(fields.get("video_url")):
            return {"type": "url", "url": fields["video_url"]}
        if not _is_empty(fields.get("video_path")):
            return {"path": fields["video_path"], "type": "video"}

    if kind in {"dataset", "table"}:
        rows_value = fields.get("preview_rows") if isinstance(fields.get("preview_rows"), list) else fields.get("rows")
        rows = rows_value if isinstance(rows_value, list) else []
        if rows:
            preview_rows = rows[:20]
            return {
                "columns": _table_columns(fields, preview_rows),
                "rows": preview_rows,
                "type": "table",
            }

    if kind == "file" and not _is_empty(fields.get("file_path") or fields.get("path")):
        return {
            "path": fields.get("file_path") or fields.get("path"),
            "type": "file",
        }

    return {"type": "none"}


def _derive_title(kind: str, fields: Mapping[str, Any]) -> str:
    title = fields.get("title")
    if isinstance(title, str) and title.strip():
        return title.strip()
    name = fields.get("name")
    if isinstance(name, str) and name.strip():
        return name.strip()
    if kind == "report":
        filename = fields.get("report_filename") or _basename(fields.get("report_path"))
        return str(filename) if filename else "Report"
    if kind == "dashboard":
        return "Dashboard preview"
    if kind == "video":
        return "Video preview"
    if kind == "dataset":
        return "Dataset"
    if kind == "table":
        return "Table"
    if kind == "file":
        filename = _basename(fields.get("file_path") or fields.get("path"))
        return filename or "File"
    return kind.replace("_", " ").title()


def _derive_summary(fields: Mapping[str, Any]) -> str | None:
    summary = fields.get("summary")
    if isinstance(summary, str) and summary.strip():
        return summary.strip()
    message = fields.get("message")
    if isinstance(message, str) and message.strip():
        return message.strip()
    error = fields.get("error")
    if isinstance(error, str) and error.strip():
        return error.strip()
    return None


def _derive_payload(fields: Mapping[str, Any]) -> dict[str, Any]:
    existing_payload = fields.get("payload")
    payload = dict(existing_payload) if isinstance(existing_payload, dict) else {}
    for key, value in fields.items():
        if key in NORMALIZED_ARTIFACT_KEYS:
            continue
        payload.setdefault(key, value)
    return payload


def normalize_workflow_artifact(
    kind: str | None = None,
    fields: Mapping[str, Any] | None = None,
    **extra_fields: Any,
) -> dict[str, Any]:
    """Return a normalized artifact payload while preserving legacy fields."""
    raw = _clean_mapping(fields)
    raw.update(_clean_mapping(extra_fields))

    artifact_kind = _clean_kind(kind or raw.get("kind"))
    raw["kind"] = artifact_kind

    normalized = dict(raw)
    normalized["kind"] = artifact_kind
    normalized["status"] = _normalize_status(raw.get("status"), raw, artifact_kind)
    normalized["title"] = _derive_title(artifact_kind, raw)

    summary = _derive_summary(raw)
    artifact = WorkflowArtifactPayload(
        **{key: value for key, value in raw.items() if key not in NORMALIZED_ARTIFACT_KEYS},
        kind=artifact_kind,
        status=_normalize_status(raw.get("status"), raw, artifact_kind),
        title=_derive_title(artifact_kind, raw),
        summary=summary,
        node_id=raw.get("node_id") if isinstance(raw.get("node_id"), str) else None,
        preview=_derive_preview(artifact_kind, raw),
        files=_merge_file_descriptors(raw.get("files"), _derive_files(artifact_kind, raw)),
        payload=_derive_payload(raw),
    )
    normalized.update(artifact.model_dump(exclude_none=True))
    return normalized


def normalize_workflow_artifacts(artifacts: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    if not artifacts:
        return []
    normalized: list[dict[str, Any]] = []
    for artifact in artifacts:
        if isinstance(artifact, dict):
            normalized.append(normalize_workflow_artifact(artifact.get("kind"), artifact))
    return normalized


def extract_workflow_artifacts(outputs: dict[str, Any] | None) -> list[dict[str, Any]]:
    """Extract known workflow artifacts from node outputs."""
    if not isinstance(outputs, dict):
        return []

    artifacts: list[dict[str, Any]] = []
    for node_id, raw_outputs in outputs.items():
        if not isinstance(raw_outputs, dict):
            continue

        report_path = raw_outputs.get("report_path")
        report_html = raw_outputs.get("report_html")
        if report_path or report_html:
            artifacts.append(
                normalize_workflow_artifact(
                    "report",
                    node_id=node_id,
                    report_path=report_path,
                    report_html=report_html,
                    report_filename=_basename(report_path) if report_path else None,
                    status=raw_outputs.get("status"),
                    message=raw_outputs.get("message"),
                )
            )

        dashboard_url = raw_outputs.get("dashboard_url")
        if dashboard_url:
            artifacts.append(
                normalize_workflow_artifact(
                    "dashboard",
                    node_id=node_id,
                    dashboard_url=dashboard_url,
                    output_path=raw_outputs.get("output_path"),
                )
            )

        if raw_outputs.get("task_id") or raw_outputs.get("video_url") or raw_outputs.get("video_path"):
            artifacts.append(
                normalize_workflow_artifact(
                    "video",
                    node_id=node_id,
                    task_id=raw_outputs.get("task_id"),
                    video_url=raw_outputs.get("video_url"),
                    video_path=raw_outputs.get("video_path"),
                    session_id=raw_outputs.get("session_id"),
                )
            )

    return artifacts
