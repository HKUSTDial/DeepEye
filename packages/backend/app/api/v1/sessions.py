"""Session management endpoints using Repository pattern."""

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
import asyncio
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.deps import CurrentUserId
from app.db.session import get_db
from app.models import ChatSession
from app.repositories import (
    DataSourceRepository,
    MessageRepository,
    SessionAttachmentRepository,
    SessionRepository,
    WorkflowDraftRepository,
)
from app.schemas import (
    ChatSessionResponse,
    DataSourceResponse,
    WorkspaceStateResponse,
    WorkflowDraftResponse,
    WorkflowDraftUpsertRequest,
    WorkflowQueuedRunResponse,
)
from app.sandbox import sandbox_manager
from app.runtime.services.preview_manager import preview_runtime_manager
from app.session.services.attachment import (
    attach_datasource_to_session,
    detach_datasource_from_session,
    list_session_attachments,
)
from app.workflow.services.file_service import (
    prepare_tracked_workflow_draft_run,
    write_workflow_definition_to_file,
)
from app.workflow.services.targets import save_workflow_draft
from app.workflow.services.tracking import build_workspace_state
from app.tasks.workflow_tasks import run_workflow_draft_task
from deepeye.utils.logger import logger

router = APIRouter(prefix="/sessions", tags=["sessions"])


class CreateSessionRequest(BaseModel):
    """Request body for creating a new session"""
    title: str = "New conversation"


class UpdateSessionRequest(BaseModel):
    """Request body for updating a session"""
    title: str


def _get_owned_session_or_404(db: Session, session_id: uuid.UUID, user_id: uuid.UUID) -> ChatSession:
    session = SessionRepository(db).get_by_id_and_user(session_id, user_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


async def _cleanup_session_runtime_resources(session_id: str) -> None:
    tasks = (
        sandbox_manager.destroy_session(session_id, delete_data=True),
        preview_runtime_manager.cleanup_session_previews(session_id),
    )
    results = await asyncio.gather(*tasks, return_exceptions=True)
    for result in results:
        if isinstance(result, Exception):
            logger.warning("Failed to cleanup runtime resources for session %s: %s", session_id, result)


@router.post("", response_model=ChatSessionResponse, status_code=status.HTTP_201_CREATED)
def create_session(
    request: CreateSessionRequest,
    user_id: CurrentUserId,  # ⭐ 自动鉴权并注入 user_id
    db: Session = Depends(get_db)
):
    """Create a new chat session."""
    session_id = uuid.uuid4()
    new_session = ChatSession(id=session_id, user_id=user_id, title=request.title[:50])
    saved_session = SessionRepository(db).save(new_session)
    return saved_session


@router.get("", response_model=list[ChatSessionResponse])
def list_sessions(
    user_id: CurrentUserId,  # ⭐ 自动鉴权并注入 user_id
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """List chat sessions for current user, most recent first."""
    return SessionRepository(db).list_by_user(user_id, skip, limit)


@router.get("/{session_id}", response_model=ChatSessionResponse)
def get_session(
    session_id: uuid.UUID,
    user_id: CurrentUserId,  # ⭐ 自动鉴权并注入 user_id
    db: Session = Depends(get_db)
):
    """Get a single session by ID (only if owned by current user)."""
    return _get_owned_session_or_404(db, session_id, user_id)


@router.patch("/{session_id}", response_model=ChatSessionResponse)
def update_session(
    session_id: uuid.UUID,
    request: UpdateSessionRequest,
    user_id: CurrentUserId,  # ⭐ 自动鉴权并注入 user_id
    db: Session = Depends(get_db)
):
    """Update session title (only if owned by current user)."""
    repo = SessionRepository(db)
    session = _get_owned_session_or_404(db, session_id, user_id)
    
    session.title = request.title[:50]  # Limit title length
    return repo.save(session)


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_session(
    session_id: uuid.UUID,
    user_id: CurrentUserId,  # ⭐ 自动鉴权并注入 user_id
    db: Session = Depends(get_db)
):
    """Delete a session and its messages (only if owned by current user)."""
    repo = SessionRepository(db)
    _get_owned_session_or_404(db, session_id, user_id)
    MessageRepository(db).delete_by_session(str(session_id))
    SessionAttachmentRepository(db).detach_all_for_session(session_id)
    repo.delete(session_id)
    try:
        asyncio.create_task(_cleanup_session_runtime_resources(str(session_id)))
    except Exception:
        pass


@router.get("/{session_id}/attachments", response_model=list[DataSourceResponse])
def get_session_attachments(
    session_id: uuid.UUID,
    user_id: CurrentUserId,
    db: Session = Depends(get_db),
):
    """List datasources attached to a session."""
    _get_owned_session_or_404(db, session_id, user_id)
    return list_session_attachments(db, session_id)


@router.post("/{session_id}/attachments/{datasource_id}", response_model=DataSourceResponse)
async def attach_session_datasource_endpoint(
    session_id: uuid.UUID,
    datasource_id: uuid.UUID,
    user_id: CurrentUserId,
    db: Session = Depends(get_db),
):
    """Attach an existing datasource to a session."""
    session = _get_owned_session_or_404(db, session_id, user_id)
    datasource = DataSourceRepository(db).get_by_id_and_user(datasource_id, user_id)
    if not datasource:
        raise HTTPException(status_code=404, detail="DataSource not found")
    return await attach_datasource_to_session(db, session, datasource)


@router.delete("/{session_id}/attachments/{datasource_id}", status_code=status.HTTP_204_NO_CONTENT)
async def detach_session_datasource_endpoint(
    session_id: uuid.UUID,
    datasource_id: uuid.UUID,
    user_id: CurrentUserId,
    db: Session = Depends(get_db),
):
    """Detach a datasource from a session without deleting it globally."""
    session = _get_owned_session_or_404(db, session_id, user_id)
    datasource = DataSourceRepository(db).get_by_id_and_user(datasource_id, user_id)
    if not datasource:
        raise HTTPException(status_code=404, detail="DataSource not found")
    detached = await detach_datasource_from_session(db, session, datasource)
    if not detached:
        raise HTTPException(status_code=404, detail="DataSource is not attached to this session")


@router.get("/{session_id}/messages")
def get_session_messages(
    session_id: str,
    user_id: CurrentUserId,  # ⭐ 自动鉴权并注入 user_id
    db: Session = Depends(get_db)
) -> dict[str, Any]:
    """Get all messages for a session (only if owned by current user)."""
    # 验证 session 归属
    session_uuid = uuid.UUID(session_id)
    _get_owned_session_or_404(db, session_uuid, user_id)
    
    return {"messages": MessageRepository(db).get_messages(session_id)}


@router.get("/{session_id}/workspace-state", response_model=WorkspaceStateResponse)
def get_session_workspace_state(
    session_id: uuid.UUID,
    user_id: CurrentUserId,
    db: Session = Depends(get_db),
):
    """Return the latest turn/draft/run/artifact snapshot for the session workspace."""
    _get_owned_session_or_404(db, session_id, user_id)
    return build_workspace_state(db, session_id)


@router.get("/{session_id}/workflow-drafts", response_model=list[WorkflowDraftResponse])
def list_session_workflow_drafts(
    session_id: uuid.UUID,
    user_id: CurrentUserId,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    """List tracked workflow drafts for the session, most recent first."""
    _get_owned_session_or_404(db, session_id, user_id)
    safe_limit = max(1, min(limit, 200))
    return WorkflowDraftRepository(db).list_by_session(session_id, limit=safe_limit)


@router.post("/{session_id}/workflow-drafts", response_model=WorkflowDraftResponse)
async def upsert_session_workflow_draft(
    session_id: uuid.UUID,
    request: WorkflowDraftUpsertRequest,
    user_id: CurrentUserId,
    db: Session = Depends(get_db),
):
    """Persist an editor workflow draft for the session and mirror it to the sandbox."""
    session = _get_owned_session_or_404(db, session_id, user_id)
    try:
        draft = save_workflow_draft(
            db,
            session_id=session.id,
            user_id=user_id,
            draft_id=request.draft_id,
            name=request.name,
            definition=request.definition,
            source="workflow_editor",
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    if draft.file_path:
        await write_workflow_definition_to_file(str(session.id), draft.file_path, request.definition)
    return draft


@router.post("/{session_id}/workflow-drafts/{draft_id}/run", response_model=WorkflowQueuedRunResponse)
async def run_session_workflow_draft(
    session_id: uuid.UUID,
    draft_id: uuid.UUID,
    user_id: CurrentUserId,
    db: Session = Depends(get_db),
):
    """Queue execution for a tracked workflow draft."""
    session = _get_owned_session_or_404(db, session_id, user_id)
    try:
        tracked_turn, tracked_draft, tracked_run, path = prepare_tracked_workflow_draft_run(
            db,
            user_id=session.user_id,
            session_id=str(session.id),
            draft_id=str(draft_id),
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    if not tracked_draft or not isinstance(tracked_draft.definition, dict):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow draft not found")

    await write_workflow_definition_to_file(str(session.id), path, tracked_draft.definition)
    task = run_workflow_draft_task.delay(
        str(session.user_id),
        str(session.id),
        str(tracked_draft.id),
        str(tracked_turn.id) if tracked_turn else None,
        str(tracked_run.id) if tracked_run else None,
    )
    return WorkflowQueuedRunResponse(
        status="queued",
        task_id=task.id,
        turn_id=tracked_turn.id if tracked_turn else None,
        draft_id=tracked_draft.id if tracked_draft else None,
        run_id=tracked_run.id if tracked_run else None,
    )
