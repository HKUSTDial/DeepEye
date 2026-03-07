"""Chat turn repository."""

import uuid

from sqlalchemy.orm import Session

from app.models.chat_turn import ChatTurn
from app.repositories.base import SQLAlchemyRepository


class ChatTurnRepository(SQLAlchemyRepository[ChatTurn, uuid.UUID]):
    def __init__(self, db: Session):
        super().__init__(db, ChatTurn)

    def get_latest_by_session(self, session_id: uuid.UUID) -> ChatTurn | None:
        return (
            self.db.query(self.model_class)
            .filter(ChatTurn.session_id == session_id)
            .order_by(ChatTurn.created_at.desc())
            .first()
        )

    def get_latest_active_by_session(self, session_id: uuid.UUID) -> ChatTurn | None:
        return (
            self.db.query(self.model_class)
            .filter(
                ChatTurn.session_id == session_id,
                ChatTurn.status.in_(["planning", "validating", "running", "summarizing"]),
            )
            .order_by(ChatTurn.created_at.desc())
            .first()
        )
