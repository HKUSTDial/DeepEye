"""Tests for refresh token repository rotation/revocation."""

import os
import uuid
from datetime import datetime, timedelta, timezone

os.environ.setdefault("ALLOW_INSECURE_DEFAULTS", "true")
os.environ.setdefault("LLM_API_KEY", "test-key")
os.environ.setdefault("LLM_BASE_URL", "http://localhost:8000")
os.environ.setdefault("LLM_MODEL", "test-model")

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.auth import create_refresh_token, hash_token
from app.models import Base, User
from app.repositories import RefreshTokenRepository


def _build_test_db():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    session_local = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    return session_local()


def _create_user(db, email: str = "alice@example.com") -> User:
    user = User(
        email=email,
        username="alice",
        hashed_password="hashed",
        is_active=True,
        is_superuser=False,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def test_refresh_token_issue_and_lookup():
    db = _build_test_db()
    try:
        user = _create_user(db)
        repo = RefreshTokenRepository(db)
        token, token_jti, expires_at = create_refresh_token(user.id, user.username, user.email)

        issued = repo.issue(
            user_id=user.id,
            token_jti=token_jti,
            token_hash=hash_token(token),
            expires_at=expires_at,
            created_by_ip="127.0.0.1",
            user_agent="pytest",
        )
        found = repo.get_active_by_jti(user.id, token_jti)

        assert issued.id is not None
        assert found is not None
        assert found.token_hash == hash_token(token)
    finally:
        db.close()


def test_refresh_token_rotate_revokes_old_token():
    db = _build_test_db()
    try:
        user = _create_user(db)
        repo = RefreshTokenRepository(db)
        token, token_jti, expires_at = create_refresh_token(user.id, user.username, user.email)
        current = repo.issue(
            user_id=user.id,
            token_jti=token_jti,
            token_hash=hash_token(token),
            expires_at=expires_at,
        )

        new_token, new_jti, new_expires_at = create_refresh_token(user.id, user.username, user.email)
        next_token = repo.rotate(
            current,
            new_token_jti=new_jti,
            new_token_hash=hash_token(new_token),
            new_expires_at=new_expires_at,
        )

        db.refresh(current)
        assert current.revoked_at is not None
        assert current.replaced_by_token_jti == new_jti
        assert repo.get_active_by_jti(user.id, token_jti) is None
        assert repo.get_active_by_jti(user.id, new_jti) is not None
        assert next_token.token_jti == new_jti
    finally:
        db.close()


def test_refresh_token_revoke_by_jti():
    db = _build_test_db()
    try:
        user = _create_user(db)
        repo = RefreshTokenRepository(db)
        token, token_jti, expires_at = create_refresh_token(user.id, user.username, user.email)
        repo.issue(
            user_id=user.id,
            token_jti=token_jti,
            token_hash=hash_token(token),
            expires_at=expires_at,
        )

        assert repo.revoke_by_jti(user.id, token_jti) is True
        assert repo.get_active_by_jti(user.id, token_jti) is None
        assert repo.revoke_by_jti(user.id, token_jti) is False
    finally:
        db.close()


def test_revoke_all_for_user():
    db = _build_test_db()
    try:
        user = _create_user(db)
        repo = RefreshTokenRepository(db)
        token1, jti1, exp1 = create_refresh_token(user.id, user.username, user.email)
        token2, jti2, exp2 = create_refresh_token(user.id, user.username, user.email)
        repo.issue(user_id=user.id, token_jti=jti1, token_hash=hash_token(token1), expires_at=exp1)
        repo.issue(user_id=user.id, token_jti=jti2, token_hash=hash_token(token2), expires_at=exp2)

        revoked_count = repo.revoke_all_for_user(user.id)
        assert revoked_count == 2
        assert repo.get_active_by_jti(user.id, jti1) is None
        assert repo.get_active_by_jti(user.id, jti2) is None
    finally:
        db.close()


def test_expired_refresh_token_not_returned():
    db = _build_test_db()
    try:
        user = _create_user(db)
        repo = RefreshTokenRepository(db)
        expired_jti = uuid.uuid4()
        repo.issue(
            user_id=user.id,
            token_jti=expired_jti,
            token_hash=hash_token("expired-token"),
            expires_at=datetime.now(timezone.utc) - timedelta(minutes=1),
        )

        assert repo.get_active_by_jti(user.id, expired_jti) is None
    finally:
        db.close()
