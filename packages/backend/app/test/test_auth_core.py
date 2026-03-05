"""Unit tests for auth core helpers."""

import os
import uuid

import pytest

os.environ.setdefault("ALLOW_INSECURE_DEFAULTS", "true")
os.environ.setdefault("LLM_API_KEY", "test-key")
os.environ.setdefault("LLM_BASE_URL", "http://localhost:8000")
os.environ.setdefault("LLM_MODEL", "test-model")

from app.core.auth import (  # noqa: E402
    create_access_token,
    create_refresh_token,
    hash_token,
    validate_password_strength,
    verify_token,
)


def test_access_token_round_trip():
    user_id = uuid.uuid4()
    token = create_access_token(user_id, "alice", "alice@example.com")
    payload = verify_token(token)
    assert payload["user_id"] == str(user_id)
    assert payload["type"] == "access"


def test_refresh_token_requires_refresh_type():
    user_id = uuid.uuid4()
    token, token_jti, expires_at = create_refresh_token(user_id, "alice", "alice@example.com")

    with pytest.raises(ValueError):
        verify_token(token)

    payload = verify_token(token, expected_type="refresh")
    assert payload["user_id"] == str(user_id)
    assert payload["type"] == "refresh"
    assert payload["jti"] == str(token_jti)
    assert expires_at.tzinfo is not None


@pytest.mark.parametrize(
    "password",
    [
        "Aa1!",
        "NoDigit!",
        "nouppercase1!",
        "NOLOWERCASE1!",
        "NoSpecial123",
    ],
)
def test_validate_password_strength_rejects_weak_passwords(password: str):
    with pytest.raises(ValueError):
        validate_password_strength(password)


def test_validate_password_strength_accepts_strong_password():
    validate_password_strength("StrongPass123!")


def test_hash_token_stable():
    token_hash = hash_token("sample-token")
    assert token_hash == hash_token("sample-token")
    assert token_hash != hash_token("another-token")
