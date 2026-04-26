"""JWT auth helpers."""

from datetime import datetime, timedelta, timezone
import hashlib
import re
import secrets
import uuid
from typing import Any, Literal

import jwt
from jwt import PyJWTError
from passlib.context import CryptContext

from app.core.config import settings

SECRET_KEY = settings.JWT_SECRET_KEY
ALGORITHM = settings.JWT_ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES
REFRESH_TOKEN_EXPIRE_DAYS = settings.REFRESH_TOKEN_EXPIRE_DAYS
TOKEN_TYPE_ACCESS = "access"
TOKEN_TYPE_REFRESH = "refresh"
ACTION_TOKEN_PURPOSE_VERIFY_EMAIL = "verify_email"
ACTION_TOKEN_PURPOSE_PASSWORD_RESET = "password_reset"

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def _create_token(
    *,
    user_id: uuid.UUID,
    username: str,
    email: str,
    token_type: Literal["access", "refresh"],
    expires_at: datetime,
    token_jti: uuid.UUID | None = None,
) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "user_id": str(user_id),
        "username": username,
        "email": email,
        "type": token_type,
        "exp": expires_at,
        "iat": now,
    }
    if token_jti is not None:
        payload["jti"] = str(token_jti)
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def create_access_token(user_id: uuid.UUID, username: str, email: str) -> str:
    """Create access token."""
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    return _create_token(
        user_id=user_id,
        username=username,
        email=email,
        token_type=TOKEN_TYPE_ACCESS,
        expires_at=expires_at,
    )


def create_refresh_token(user_id: uuid.UUID, username: str, email: str) -> tuple[str, uuid.UUID, datetime]:
    """Create refresh token and return token + jti + expiry."""
    token_jti = uuid.uuid4()
    expires_at = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    token = _create_token(
        user_id=user_id,
        username=username,
        email=email,
        token_type=TOKEN_TYPE_REFRESH,
        expires_at=expires_at,
        token_jti=token_jti,
    )
    return token, token_jti, expires_at


def verify_token(
    token: str,
    *,
    expected_type: Literal["access", "refresh"] | None = TOKEN_TYPE_ACCESS,
    allow_expired: bool = False,
) -> dict[str, Any]:
    """Verify JWT token and optional token type."""
    try:
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM],
            options={"verify_exp": not allow_expired},
        )
    except PyJWTError as e:
        raise ValueError(f"Invalid token: {str(e)}") from e

    if expected_type:
        # Backward compatibility: legacy access tokens may not include `type`.
        actual_type = payload.get("type", TOKEN_TYPE_ACCESS)
        if actual_type != expected_type:
            raise ValueError("Invalid token type")
    return payload


def validate_password_strength(password: str) -> None:
    """Validate password strength for registration."""
    if len(password) < 8 or len(password) > 64:
        raise ValueError("Password must be 8-64 characters long")
    if not re.search(r"[a-z]", password):
        raise ValueError("Password must include at least one lowercase letter")
    if not re.search(r"[A-Z]", password):
        raise ValueError("Password must include at least one uppercase letter")
    if not re.search(r"\d", password):
        raise ValueError("Password must include at least one digit")
    if not re.search(r"[^A-Za-z0-9]", password):
        raise ValueError("Password must include at least one special character")


def _truncate_password(password: str, max_bytes: int = 72) -> str:
    """Truncate password for bcrypt 72-byte limit while preserving UTF-8."""
    password_bytes = password.encode("utf-8")
    if len(password_bytes) <= max_bytes:
        return password
    return password_bytes[:max_bytes].decode("utf-8", errors="ignore")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify plain password against hash."""
    truncated = _truncate_password(plain_password)
    return pwd_context.verify(truncated, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash password with bcrypt."""
    truncated = _truncate_password(password)
    return pwd_context.hash(truncated)


def hash_token(token: str) -> str:
    """Hash opaque token value for DB storage."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_action_token(*, expires_in_minutes: int) -> tuple[str, str, datetime]:
    """Create one-time action token with hashed form and expiry."""
    token = secrets.token_urlsafe(48)
    token_hash = hash_token(token)
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=expires_in_minutes)
    return token, token_hash, expires_at
