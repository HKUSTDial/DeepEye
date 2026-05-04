from __future__ import annotations

import os
import uuid

from sqlalchemy.orm import Session

from app.models import WorkflowDraft
from app.repositories import WorkflowDraftRepository
from app.workflow.services.tracking import upsert_workflow_draft

WORKFLOW_DIR = "/workspace/workflow"


def _as_uuid(value: str | uuid.UUID | None) -> uuid.UUID | None:
    if value is None or isinstance(value, uuid.UUID):
        return value
    try:
        return uuid.UUID(str(value))
    except (TypeError, ValueError):
        return None


def sanitize_workflow_name(name: str) -> str:
    base = name.strip()
    if base.lower().endswith(".json"):
        base = base[:-5]
    clean = "".join(ch for ch in base if ch.isalnum() or ch in ("-", "_"))
    if not clean:
        clean = "workflow"
    return f"{clean}.json"


def normalize_workflow_path(path: str) -> str:
    clean = path.strip()
    filename = os.path.basename(clean)
    return f"{WORKFLOW_DIR}/{sanitize_workflow_name(filename)}"


def build_default_workflow_path(*, name: str | None = None, draft_id: str | uuid.UUID | None = None) -> str:
    if name:
        return f"{WORKFLOW_DIR}/{sanitize_workflow_name(name)}"
    if draft_id:
        normalized = str(draft_id).replace("-", "")
        return f"{WORKFLOW_DIR}/draft_{normalized[:12]}.json"
    return f"{WORKFLOW_DIR}/workflow.json"


def resolve_workflow_target(
    db: Session,
    session_id: str | uuid.UUID,
    *,
    draft_id: str | uuid.UUID | None = None,
    file_path: str | None = None,
    name: str | None = None,
) -> tuple[WorkflowDraft | None, str]:
    session_uuid = _as_uuid(session_id)
    if not session_uuid:
        raise ValueError("Invalid session_id")

    existing_draft = None
    draft_uuid = _as_uuid(draft_id)
    if draft_uuid:
        existing_draft = WorkflowDraftRepository(db).get(draft_uuid)
        if not existing_draft:
            raise ValueError("Workflow draft not found.")
        if existing_draft.session_id != session_uuid:
            raise ValueError("Workflow draft does not belong to the current session.")

    if existing_draft and existing_draft.file_path:
        return existing_draft, existing_draft.file_path
    if file_path:
        return existing_draft, normalize_workflow_path(file_path)
    if name:
        return existing_draft, build_default_workflow_path(name=name)
    if existing_draft:
        return existing_draft, build_default_workflow_path(draft_id=existing_draft.id)
    return None, build_default_workflow_path()


def save_workflow_draft(
    db: Session,
    *,
    session_id: str | uuid.UUID,
    user_id: str | uuid.UUID,
    definition: dict,
    turn_id: str | uuid.UUID | None = None,
    draft_id: str | uuid.UUID | None = None,
    file_path: str | None = None,
    name: str | None = None,
    source: str = "workflow_agent",
) -> WorkflowDraft:
    existing_draft, resolved_path = resolve_workflow_target(
        db,
        session_id,
        draft_id=draft_id,
        file_path=file_path,
        name=name,
    )

    if existing_draft:
        desired_turn_id = _as_uuid(turn_id)
        definition_changed = existing_draft.definition != definition
        path_changed = existing_draft.file_path != resolved_path
        metadata_changed = (
            existing_draft.turn_id != desired_turn_id
            or existing_draft.source != source
            or existing_draft.status != "draft"
        )
        if not definition_changed and not path_changed and not metadata_changed:
            return existing_draft
        existing_draft.definition = definition
        existing_draft.file_path = resolved_path
        existing_draft.turn_id = desired_turn_id
        existing_draft.source = source
        existing_draft.status = "draft"
        if definition_changed or path_changed:
            existing_draft.version = max(1, existing_draft.version + 1)
        return WorkflowDraftRepository(db).save(existing_draft)

    user_uuid = _as_uuid(user_id)
    if not user_uuid:
        raise ValueError("Invalid user_id")
    return upsert_workflow_draft(
        db,
        session_id=session_id,
        user_id=user_uuid,
        definition=definition,
        file_path=resolved_path,
        turn_id=turn_id,
        source=source,
    )
