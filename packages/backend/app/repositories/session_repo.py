"""Session Repository."""

import uuid

from sqlalchemy.orm import Session

from app.models import ChatSession
from app.repositories.base import SQLAlchemyRepository


class SessionRepository(SQLAlchemyRepository[ChatSession, uuid.UUID]):
    """Repository for ChatSession entities."""

    def __init__(self, db: Session):
        super().__init__(db, ChatSession)

    def list_recent(self, skip: int = 0, limit: int = 100) -> list[ChatSession]:
        """List sessions ordered by updated_at descending."""
        return self.find_all_desc("updated_at", skip, limit)
    
    def list_by_user(self, user_id: uuid.UUID, skip: int = 0, limit: int = 100) -> list[ChatSession]:
        """List sessions for a specific user, ordered by updated_at descending."""
        return (
            self.db.query(self.model_class)
            .filter(ChatSession.user_id == user_id)
            .order_by(ChatSession.updated_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )
    
    def get_by_id_and_user(self, session_id: uuid.UUID, user_id: uuid.UUID) -> ChatSession | None:
        """Get a session by ID, but only if it belongs to the specified user."""
        return (
            self.db.query(self.model_class)
            .filter(ChatSession.id == session_id, ChatSession.user_id == user_id)
            .first()
        )
