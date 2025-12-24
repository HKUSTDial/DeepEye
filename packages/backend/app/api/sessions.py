"""Session management endpoints using Repository pattern."""

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.repositories import MessageRepository, SessionRepository
from app.schemas import ChatSessionResponse

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.get("", response_model=list[ChatSessionResponse])
def list_sessions(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """List chat sessions, most recent first."""
    return SessionRepository(db).list_recent(skip, limit)


@router.get("/{session_id}", response_model=ChatSessionResponse)
def get_session(session_id: uuid.UUID, db: Session = Depends(get_db)):
    """Get a single session by ID."""
    session = SessionRepository(db).get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_session(session_id: uuid.UUID, db: Session = Depends(get_db)):
    """Delete a session and its messages."""
    repo = SessionRepository(db)
    if not repo.get(session_id):
        raise HTTPException(status_code=404, detail="Session not found")
    MessageRepository(db).delete_by_session(str(session_id))
    repo.delete(session_id)


@router.get("/{session_id}/messages")
def get_session_messages(session_id: str, db: Session = Depends(get_db)) -> dict[str, Any]:
    """Get all messages (user + assistant) for a session."""
    return {"messages": MessageRepository(db).get_messages(session_id)}

