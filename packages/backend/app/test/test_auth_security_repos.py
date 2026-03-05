"""Tests for auth action/audit/verification repositories."""

import os
from datetime import datetime, timedelta, timezone

os.environ.setdefault("ALLOW_INSECURE_DEFAULTS", "true")
os.environ.setdefault("LLM_API_KEY", "test-key")
os.environ.setdefault("LLM_BASE_URL", "http://localhost:8000")
os.environ.setdefault("LLM_MODEL", "test-model")

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.auth import (
    ACTION_TOKEN_PURPOSE_PASSWORD_RESET,
    ACTION_TOKEN_PURPOSE_VERIFY_EMAIL,
    create_action_token,
    hash_token,
)
from app.models import Base, User
from app.repositories import AuthActionTokenRepository, AuthAuditRepository, UserEmailVerificationRepository


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


def test_action_token_issue_consume_once():
    db = _build_test_db()
    try:
        user = _create_user(db)
        repo = AuthActionTokenRepository(db)
        token, token_hash, expires_at = create_action_token(expires_in_minutes=15)
        issued = repo.issue(
            user_id=user.id,
            purpose=ACTION_TOKEN_PURPOSE_VERIFY_EMAIL,
            token_hash=token_hash,
            expires_at=expires_at,
            requested_by_ip="127.0.0.1",
            user_agent="pytest",
        )
        consumed = repo.consume(
            purpose=ACTION_TOKEN_PURPOSE_VERIFY_EMAIL,
            token_hash=hash_token(token),
            consumed_by_ip="127.0.0.1",
        )
        consumed_again = repo.consume(
            purpose=ACTION_TOKEN_PURPOSE_VERIFY_EMAIL,
            token_hash=hash_token(token),
            consumed_by_ip="127.0.0.1",
        )

        assert issued.id is not None
        assert consumed is not None
        assert consumed.used_at is not None
        assert consumed_again is None
    finally:
        db.close()


def test_action_token_revoke_active_for_user():
    db = _build_test_db()
    try:
        user = _create_user(db)
        repo = AuthActionTokenRepository(db)
        for _ in range(2):
            raw, token_hash, expires_at = create_action_token(expires_in_minutes=15)
            repo.issue(
                user_id=user.id,
                purpose=ACTION_TOKEN_PURPOSE_PASSWORD_RESET,
                token_hash=token_hash,
                expires_at=expires_at,
            )
            assert raw
        revoked = repo.revoke_active_for_user(user.id, ACTION_TOKEN_PURPOSE_PASSWORD_RESET)
        assert revoked == 2
    finally:
        db.close()


def test_action_token_expired_not_consumed():
    db = _build_test_db()
    try:
        user = _create_user(db)
        repo = AuthActionTokenRepository(db)
        token_hash = hash_token("expired")
        repo.issue(
            user_id=user.id,
            purpose=ACTION_TOKEN_PURPOSE_PASSWORD_RESET,
            token_hash=token_hash,
            expires_at=datetime.now(timezone.utc) - timedelta(minutes=1),
        )
        assert repo.consume(
            purpose=ACTION_TOKEN_PURPOSE_PASSWORD_RESET,
            token_hash=token_hash,
        ) is None
    finally:
        db.close()


def test_email_verification_repo_mark_and_check():
    db = _build_test_db()
    try:
        user = _create_user(db)
        repo = UserEmailVerificationRepository(db)
        assert repo.is_verified(user.id) is False
        record = repo.mark_verified(user.id)
        assert record.user_id == user.id
        assert repo.is_verified(user.id) is True
    finally:
        db.close()


def test_auth_audit_repo_log():
    db = _build_test_db()
    try:
        user = _create_user(db)
        repo = AuthAuditRepository(db)
        event = repo.log(
            event_type="login",
            success=True,
            user_id=user.id,
            email=user.email,
            ip_address="127.0.0.1",
            detail="login_success",
        )
        assert event.id is not None
        assert event.event_type == "login"
        assert event.success is True
    finally:
        db.close()
