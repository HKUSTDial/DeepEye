"""User email verification repository."""

import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models import UserEmailVerification
from app.repositories.base import SQLAlchemyRepository


class UserEmailVerificationRepository(SQLAlchemyRepository[UserEmailVerification, uuid.UUID]):
    """Repository for email verification state."""

    def __init__(self, db: Session):
        super().__init__(db, UserEmailVerification)

    def is_verified(self, user_id: uuid.UUID) -> bool:
        return (
            self.db.query(self.model_class)
            .filter(UserEmailVerification.user_id == user_id)
            .first()
            is not None
        )

    def mark_verified(self, user_id: uuid.UUID, verified_at: datetime | None = None) -> UserEmailVerification:
        now = verified_at or datetime.now(timezone.utc)
        record = (
            self.db.query(self.model_class)
            .filter(UserEmailVerification.user_id == user_id)
            .first()
        )
        if record:
            record.verified_at = now
            self.db.add(record)
            self.db.commit()
            self.db.refresh(record)
            return record

        record = UserEmailVerification(user_id=user_id, verified_at=now)
        return self.save(record)
