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
from app.repositories import DataSourceRepository, MessageRepository, SessionAttachmentRepository, SessionRepository
from app.schemas import ChatSessionResponse, DataSourceResponse
from app.sandbox import sandbox_manager
from app.services import attach_datasource_to_session, detach_datasource_from_session, list_session_attachments

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
        asyncio.create_task(sandbox_manager.destroy_session(str(session_id), delete_data=True))
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
