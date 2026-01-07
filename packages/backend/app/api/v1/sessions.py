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
from app.repositories import MessageRepository, SessionRepository
from app.schemas import ChatSessionResponse
from app.sandbox import sandbox_manager

router = APIRouter(prefix="/sessions", tags=["sessions"])


class CreateSessionRequest(BaseModel):
    """Request body for creating a new session"""
    title: str = "New conversation"


class UpdateSessionRequest(BaseModel):
    """Request body for updating a session"""
    title: str


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
    session = SessionRepository(db).get_by_id_and_user(session_id, user_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@router.patch("/{session_id}", response_model=ChatSessionResponse)
def update_session(
    session_id: uuid.UUID,
    request: UpdateSessionRequest,
    user_id: CurrentUserId,  # ⭐ 自动鉴权并注入 user_id
    db: Session = Depends(get_db)
):
    """Update session title (only if owned by current user)."""
    repo = SessionRepository(db)
    session = repo.get_by_id_and_user(session_id, user_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
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
    if not repo.get_by_id_and_user(session_id, user_id):
        raise HTTPException(status_code=404, detail="Session not found")
    MessageRepository(db).delete_by_session(str(session_id))
    repo.delete(session_id)
    try:
        asyncio.create_task(sandbox_manager.destroy_session(str(session_id), delete_data=True))
    except Exception:
        pass


@router.get("/{session_id}/messages")
def get_session_messages(
    session_id: str,
    user_id: CurrentUserId,  # ⭐ 自动鉴权并注入 user_id
    db: Session = Depends(get_db)
) -> dict[str, Any]:
    """Get all messages for a session (only if owned by current user)."""
    # 验证 session 归属
    session_uuid = uuid.UUID(session_id)
    if not SessionRepository(db).get_by_id_and_user(session_uuid, user_id):
        raise HTTPException(status_code=404, detail="Session not found")
    
    return {"messages": MessageRepository(db).get_messages(session_id)}
