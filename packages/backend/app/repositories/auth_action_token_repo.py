"""Auth action token repository."""

import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models import AuthActionToken
from app.repositories.base import SQLAlchemyRepository


class AuthActionTokenRepository(SQLAlchemyRepository[AuthActionToken, uuid.UUID]):
    """Repository for one-time auth action tokens."""

    def __init__(self, db: Session):
        super().__init__(db, AuthActionToken)

    def revoke_active_for_user(self, user_id: uuid.UUID, purpose: str) -> int:
        now = datetime.now(timezone.utc)
        tokens = (
            self.db.query(self.model_class)
            .filter(
                AuthActionToken.user_id == user_id,
                AuthActionToken.purpose == purpose,
                AuthActionToken.used_at.is_(None),
                AuthActionToken.expires_at > now,
            )
            .all()
        )
        for token in tokens:
            token.used_at = now
            self.db.add(token)
        self.db.commit()
        return len(tokens)

    def issue(
        self,
        *,
        user_id: uuid.UUID,
        purpose: str,
        token_hash: str,
        expires_at: datetime,
        requested_by_ip: str | None = None,
        user_agent: str | None = None,
    ) -> AuthActionToken:
        token = AuthActionToken(
            user_id=user_id,
            purpose=purpose,
            token_hash=token_hash,
            expires_at=expires_at,
            requested_by_ip=requested_by_ip,
            user_agent=user_agent,
        )
        return self.save(token)

    def consume(self, *, purpose: str, token_hash: str, consumed_by_ip: str | None = None) -> AuthActionToken | None:
        now = datetime.now(timezone.utc)
        token = (
            self.db.query(self.model_class)
            .filter(
                AuthActionToken.purpose == purpose,
                AuthActionToken.token_hash == token_hash,
                AuthActionToken.used_at.is_(None),
                AuthActionToken.expires_at > now,
            )
            .first()
        )
        if not token:
            return None

        token.used_at = now
        token.consumed_by_ip = consumed_by_ip
        self.db.add(token)
        self.db.commit()
        self.db.refresh(token)
        return token
