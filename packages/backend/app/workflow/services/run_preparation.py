from __future__ import annotations

import uuid

from app.repositories import WorkflowDraftRepository, WorkflowRunRepository
from app.workflow.services.targets import resolve_workflow_target
from app.workflow.services.tracking import (
    create_tracked_workflow_run,
    get_chat_turn,
    get_latest_active_turn,
    upsert_workflow_draft,
)


def _as_uuid(value: str | uuid.UUID | None) -> uuid.UUID | None:
    if value is None or isinstance(value, uuid.UUID):
        return value
    try:
        return uuid.UUID(str(value))
    except (TypeError, ValueError):
        return None


def prepare_tracked_workflow_file_run(
    db,
    *,
    user_id,
    session_id: str,
    path: str,
    definition: dict,
    turn_id: str | None = None,
    draft_id: str | None = None,
    run_id: str | None = None,
):
    return prepare_tracked_workflow_run(
        db,
        user_id=user_id,
        session_id=session_id,
        path=path,
        definition=definition,
        turn_id=turn_id,
        draft_id=draft_id,
        run_id=run_id,
        draft_source="workflow_file",
        run_source="workflow_file",
    )


def prepare_tracked_workflow_run(
    db,
    *,
    user_id,
    session_id: str,
    definition: dict,
    path: str | None = None,
    turn_id: str | None = None,
    draft_id: str | None = None,
    run_id: str | None = None,
    draft_source: str | None = None,
    run_source: str = "workflow_file",
):
    tracked_turn = get_chat_turn(db, turn_id) if turn_id else get_latest_active_turn(db, session_id)

    draft_repo = WorkflowDraftRepository(db)
    tracked_draft = draft_repo.get(_as_uuid(draft_id)) if draft_id else None
    if tracked_draft:
        tracked_draft.definition = definition
        tracked_draft.file_path = path
        tracked_draft.turn_id = tracked_turn.id if tracked_turn else None
        tracked_draft.status = "draft"
        if draft_source:
            tracked_draft.source = draft_source
        tracked_draft.version = max(1, tracked_draft.version)
        tracked_draft = draft_repo.save(tracked_draft)
    else:
        tracked_draft = upsert_workflow_draft(
            db,
            session_id=session_id,
            user_id=user_id,
            definition=definition,
            file_path=path,
            turn_id=tracked_turn.id if tracked_turn else None,
            source=draft_source or run_source,
        )

    run_repo = WorkflowRunRepository(db)
    tracked_run = run_repo.get(_as_uuid(run_id)) if run_id else None
    if tracked_run:
        tracked_run.session_id = tracked_draft.session_id
        tracked_run.turn_id = tracked_turn.id if tracked_turn else None
        tracked_run.draft_id = tracked_draft.id if tracked_draft else None
        tracked_run.file_path = path
        tracked_run.source = run_source
        tracked_run.status = "running"
        tracked_run.result = None
        tracked_run.artifacts = None
        tracked_run.error = None
        tracked_run.finished_at = None
        tracked_run = run_repo.save(tracked_run)
    else:
        tracked_run = create_tracked_workflow_run(
            db,
            user_id=user_id,
            session_id=session_id,
            turn_id=tracked_turn.id if tracked_turn else None,
            draft_id=tracked_draft.id if tracked_draft else None,
            file_path=path,
            source=run_source,
        )

    return tracked_turn, tracked_draft, tracked_run


def prepare_tracked_workflow_draft_run(
    db,
    *,
    user_id,
    session_id: str,
    draft_id: str,
    turn_id: str | None = None,
    run_id: str | None = None,
):
    tracked_draft, path = resolve_workflow_target(
        db,
        session_id,
        draft_id=draft_id,
    )
    if not tracked_draft or not isinstance(tracked_draft.definition, dict):
        raise ValueError("Workflow draft not found.")
    tracked_turn, tracked_draft, tracked_run = prepare_tracked_workflow_run(
        db,
        user_id=user_id,
        session_id=session_id,
        definition=tracked_draft.definition,
        path=path,
        turn_id=turn_id,
        draft_id=str(tracked_draft.id),
        run_id=run_id,
        draft_source=None,
        run_source="workflow_draft",
    )
    return tracked_turn, tracked_draft, tracked_run, path
