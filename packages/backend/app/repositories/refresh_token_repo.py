"""Refresh token repository."""

import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models import RefreshToken
from app.repositories.base import SQLAlchemyRepository


class RefreshTokenRepository(SQLAlchemyRepository[RefreshToken, uuid.UUID]):
    """Repository for refresh token records."""

    def __init__(self, db: Session):
        super().__init__(db, RefreshToken)

    def issue(
        self,
        *,
        user_id: uuid.UUID,
        token_jti: uuid.UUID,
        token_hash: str,
        expires_at: datetime,
        created_by_ip: str | None = None,
        user_agent: str | None = None,
    ) -> RefreshToken:
        token = RefreshToken(
            user_id=user_id,
            token_jti=token_jti,
            token_hash=token_hash,
            expires_at=expires_at,
            created_by_ip=created_by_ip,
            user_agent=user_agent,
        )
        return self.save(token)

    def get_active_by_jti(self, user_id: uuid.UUID, token_jti: uuid.UUID) -> RefreshToken | None:
        now = datetime.now(timezone.utc)
        return (
            self.db.query(self.model_class)
            .filter(
                RefreshToken.user_id == user_id,
                RefreshToken.token_jti == token_jti,
                RefreshToken.revoked_at.is_(None),
                RefreshToken.expires_at > now,
            )
            .first()
        )

    def rotate(
        self,
        current_token: RefreshToken,
        *,
        new_token_jti: uuid.UUID,
        new_token_hash: str,
        new_expires_at: datetime,
        created_by_ip: str | None = None,
        user_agent: str | None = None,
    ) -> RefreshToken:
        now = datetime.now(timezone.utc)
        current_token.revoked_at = now
        current_token.replaced_by_token_jti = new_token_jti

        next_token = RefreshToken(
            user_id=current_token.user_id,
            token_jti=new_token_jti,
            token_hash=new_token_hash,
            expires_at=new_expires_at,
            created_by_ip=created_by_ip,
            user_agent=user_agent,
        )

        self.db.add(current_token)
        self.db.add(next_token)
        self.db.commit()
        self.db.refresh(next_token)
        return next_token

    def revoke_by_jti(self, user_id: uuid.UUID, token_jti: uuid.UUID) -> bool:
        token = (
            self.db.query(self.model_class)
            .filter(
                RefreshToken.user_id == user_id,
                RefreshToken.token_jti == token_jti,
                RefreshToken.revoked_at.is_(None),
            )
            .first()
        )
        if not token:
            return False

        token.revoked_at = datetime.now(timezone.utc)
        self.db.add(token)
        self.db.commit()
        return True

    def revoke_all_for_user(self, user_id: uuid.UUID) -> int:
        tokens = (
            self.db.query(self.model_class)
            .filter(
                RefreshToken.user_id == user_id,
                RefreshToken.revoked_at.is_(None),
            )
            .all()
        )
        now = datetime.now(timezone.utc)
        for token in tokens:
            token.revoked_at = now
            self.db.add(token)
        self.db.commit()
        return len(tokens)
