"""Persistence helpers for chat turns, workflow drafts, runs, and artifacts."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, TypeVar

from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models import ChatTurn, WorkflowArtifact, WorkflowDraft, WorkflowRun
from app.repositories import (
    ChatTurnRepository,
    WorkflowArtifactRepository,
    WorkflowDraftRepository,
    WorkflowRunRepository,
)
from app.workflow.services.datasets import compact_value_for_transport, compact_workflow_result
from app.workflow.artifacts import normalize_workflow_artifact
from app.workflow.lifecycle import next_turn_status_after_run_finalized


TrackedRecord = TypeVar("TrackedRecord")


def _as_uuid(value: str | uuid.UUID | None) -> uuid.UUID | None:
    if value is None or isinstance(value, uuid.UUID):
        return value
    try:
        return uuid.UUID(str(value))
    except (TypeError, ValueError):
        return None


def _select_latest(
    preferred: TrackedRecord | None,
    fallback: TrackedRecord | None,
    *,
    key: str,
) -> TrackedRecord | None:
    if preferred is None:
        return fallback
    if fallback is None:
        return preferred
    preferred_value = getattr(preferred, key, None)
    fallback_value = getattr(fallback, key, None)
    if preferred_value is None:
        return fallback
    if fallback_value is None:
        return preferred
    return fallback if fallback_value > preferred_value else preferred


def create_chat_turn(
    db: Session,
    session_id: str | uuid.UUID,
    user_id: uuid.UUID,
    input_text: str,
    *,
    user_message_id: int | None = None,
    status: str = "planning",
) -> ChatTurn:
    session_uuid = _as_uuid(session_id)
    if not session_uuid:
        raise ValueError("Invalid session_id")
    turn = ChatTurn(
        session_id=session_uuid,
        user_id=user_id,
        user_message_id=user_message_id,
        input_text=input_text,
        status=status,
    )
    return ChatTurnRepository(db).save(turn)


def create_chat_turn_record(
    session_id: str | uuid.UUID,
    user_id: str | uuid.UUID | None,
    input_text: str,
    *,
    user_message_id: int | None = None,
    status: str = "planning",
) -> ChatTurn | None:
    user_uuid = _as_uuid(user_id)
    if not user_uuid:
        return None
    db = SessionLocal()
    try:
        return create_chat_turn(
            db,
            session_id,
            user_uuid,
            input_text,
            user_message_id=user_message_id,
            status=status,
        )
    finally:
        db.close()


def get_chat_turn(db: Session, turn_id: str | uuid.UUID | None) -> ChatTurn | None:
    turn_uuid = _as_uuid(turn_id)
    if not turn_uuid:
        return None
    return ChatTurnRepository(db).get(turn_uuid)


def get_latest_active_turn(db: Session, session_id: str | uuid.UUID) -> ChatTurn | None:
    session_uuid = _as_uuid(session_id)
    if not session_uuid:
        return None
    return ChatTurnRepository(db).get_latest_active_by_session(session_uuid)


def update_chat_turn(
    db: Session,
    turn: ChatTurn,
    *,
    status: str | None = None,
    assistant_message_id: int | None = None,
    error: str | None = None,
    finished: bool = False,
) -> ChatTurn:
    if status is not None:
        turn.status = status
    if assistant_message_id is not None:
        turn.assistant_message_id = assistant_message_id
    if error is not None:
        turn.error = error
    if finished:
        turn.finished_at = datetime.now(timezone.utc)
    return ChatTurnRepository(db).save(turn)


def complete_chat_turn_record(turn_id: str | uuid.UUID | None, *, assistant_message_id: int | None = None) -> ChatTurn | None:
    db = SessionLocal()
    try:
        turn = get_chat_turn(db, turn_id)
        if not turn:
            return None
        return update_chat_turn(
            db,
            turn,
            status="completed",
            assistant_message_id=assistant_message_id,
            finished=True,
        )
    finally:
        db.close()


def fail_chat_turn_record(
    turn_id: str | uuid.UUID | None,
    error: str,
    *,
    assistant_message_id: int | None = None,
) -> ChatTurn | None:
    db = SessionLocal()
    try:
        turn = get_chat_turn(db, turn_id)
        if not turn:
            return None
        return update_chat_turn(
            db,
            turn,
            status="failed",
            assistant_message_id=assistant_message_id,
            error=error,
            finished=True,
        )
    finally:
        db.close()


def upsert_workflow_draft(
    db: Session,
    *,
    session_id: str | uuid.UUID,
    user_id: uuid.UUID,
    definition: dict[str, Any],
    file_path: str | None = None,
    turn_id: str | uuid.UUID | None = None,
    source: str = "workflow_agent",
) -> WorkflowDraft:
    session_uuid = _as_uuid(session_id)
    turn_uuid = _as_uuid(turn_id)
    if not session_uuid:
        raise ValueError("Invalid session_id")

    repo = WorkflowDraftRepository(db)
    existing = None
    if turn_uuid:
        existing = repo.get_latest_by_turn(turn_uuid)
    elif session_uuid and file_path:
        existing = repo.get_latest_by_session_and_path(session_uuid, file_path)

    if existing:
        existing.definition = definition
        existing.file_path = file_path
        existing.source = source
        existing.status = "draft"
        existing.version += 1
        return repo.save(existing)

    draft = WorkflowDraft(
        session_id=session_uuid,
        turn_id=turn_uuid,
        user_id=user_id,
        source=source,
        status="draft",
        file_path=file_path,
        definition=definition,
        version=1,
    )
    return repo.save(draft)


def upsert_workflow_draft_record(
    *,
    session_id: str | uuid.UUID,
    user_id: str | uuid.UUID | None,
    definition: dict[str, Any],
    file_path: str | None = None,
    turn_id: str | uuid.UUID | None = None,
    source: str = "workflow_agent",
) -> WorkflowDraft | None:
    user_uuid = _as_uuid(user_id)
    if not user_uuid:
        return None
    db = SessionLocal()
    try:
        return upsert_workflow_draft(
            db,
            session_id=session_id,
            user_id=user_uuid,
            definition=definition,
            file_path=file_path,
            turn_id=turn_id,
            source=source,
        )
    finally:
        db.close()


def create_tracked_workflow_run(
    db: Session,
    *,
    user_id: uuid.UUID,
    session_id: str | uuid.UUID,
    turn_id: str | uuid.UUID | None = None,
    draft_id: str | uuid.UUID | None = None,
    file_path: str | None = None,
    workflow_id: str | uuid.UUID | None = None,
    source: str = "chat_workflow",
) -> WorkflowRun:
    session_uuid = _as_uuid(session_id)
    if not session_uuid:
        raise ValueError("Invalid session_id")
    run = WorkflowRun(
        workflow_id=_as_uuid(workflow_id),
        user_id=user_id,
        session_id=session_uuid,
        turn_id=_as_uuid(turn_id),
        draft_id=_as_uuid(draft_id),
        source=source,
        file_path=file_path,
        status="running",
        created_at=datetime.now(timezone.utc),
    )
    saved = WorkflowRunRepository(db).save(run)
    if saved.turn_id:
        turn = ChatTurnRepository(db).get(saved.turn_id)
        if turn:
            update_chat_turn(db, turn, status="running")
    return saved


def finalize_tracked_workflow_run(
    db: Session,
    run: WorkflowRun,
    *,
    status: str,
    result: dict[str, Any] | None = None,
    error: str | None = None,
    artifacts: list[dict[str, Any]] | None = None,
) -> WorkflowRun:
    run.status = status
    run.result = compact_workflow_result(result)
    run.error = error
    run.artifacts = compact_value_for_transport(artifacts) if artifacts is not None else None
    run.finished_at = datetime.now(timezone.utc)
    saved = WorkflowRunRepository(db).save(run)
    if saved.turn_id:
        turn = ChatTurnRepository(db).get(saved.turn_id)
        next_turn_status = next_turn_status_after_run_finalized(status, getattr(turn, "status", None))
        if turn and next_turn_status:
            update_chat_turn(db, turn, status=next_turn_status)
    return saved


def replace_workflow_artifacts(
    db: Session,
    run: WorkflowRun,
    artifacts: list[dict[str, Any]],
) -> list[WorkflowArtifact]:
    repo = WorkflowArtifactRepository(db)
    repo.delete_by_run(run.id)
    created: list[WorkflowArtifact] = []
    for artifact in artifacts:
        normalized_artifact = normalize_workflow_artifact(artifact.get("kind"), artifact)
        record = WorkflowArtifact(
            run_id=run.id,
            session_id=run.session_id,
            turn_id=run.turn_id,
            draft_id=run.draft_id,
            kind=str(normalized_artifact.get("kind") or "artifact"),
            payload=normalized_artifact,
        )
        created.append(repo.save(record))
    return created


def build_workspace_state(db: Session, session_id: str | uuid.UUID) -> dict[str, Any]:
    session_uuid = _as_uuid(session_id)
    if not session_uuid:
        raise ValueError("Invalid session_id")

    turn_repo = ChatTurnRepository(db)
    draft_repo = WorkflowDraftRepository(db)
    run_repo = WorkflowRunRepository(db)
    artifact_repo = WorkflowArtifactRepository(db)

    latest_turn = turn_repo.get_latest_by_session(session_uuid)
    turn_draft = draft_repo.get_latest_by_turn(latest_turn.id) if latest_turn else None
    turn_run = run_repo.get_latest_by_turn(latest_turn.id) if latest_turn else None
    session_draft = draft_repo.get_latest_by_session(session_uuid)
    session_run = run_repo.get_latest_by_session(session_uuid)

    draft = _select_latest(turn_draft, session_draft, key="updated_at")
    run = _select_latest(turn_run, session_run, key="created_at")
    if run and run.draft_id:
        run_draft = draft_repo.get(run.draft_id)
        if run_draft is not None:
            draft = _select_latest(draft, run_draft, key="updated_at")

    turn = None
    if run and run.turn_id:
        turn = turn_repo.get(run.turn_id)
    elif draft and draft.turn_id:
        turn = turn_repo.get(draft.turn_id)
    elif latest_turn and not draft and not run:
        turn = latest_turn

    artifacts = artifact_repo.list_by_run(run.id) if run else ([] if turn is None else artifact_repo.list_by_turn(turn.id))
    return {
        "session_id": session_uuid,
        "turn": turn,
        "draft": draft,
        "run": run,
        "artifacts": artifacts,
    }


def build_workspace_state_for_turn(db: Session, turn_id: str | uuid.UUID) -> dict[str, Any]:
    turn_uuid = _as_uuid(turn_id)
    if not turn_uuid:
        raise ValueError("Invalid turn_id")

    turn_repo = ChatTurnRepository(db)
    draft_repo = WorkflowDraftRepository(db)
    run_repo = WorkflowRunRepository(db)
    artifact_repo = WorkflowArtifactRepository(db)

    turn = turn_repo.get(turn_uuid)
    if turn is None:
        raise ValueError("Chat turn not found")

    draft = draft_repo.get_latest_by_turn(turn_uuid)
    run = run_repo.get_latest_by_turn(turn_uuid)
    if run and run.draft_id:
        run_draft = draft_repo.get(run.draft_id)
        if run_draft is not None:
            draft = _select_latest(draft, run_draft, key="updated_at")

    artifacts = artifact_repo.list_by_run(run.id) if run else artifact_repo.list_by_turn(turn_uuid)
    return {
        "session_id": turn.session_id,
        "turn": turn,
        "draft": draft,
        "run": run,
        "artifacts": artifacts,
    }
