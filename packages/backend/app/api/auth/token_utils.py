"""Auth token extraction helpers."""

from fastapi import Request

from app.core.config import settings


def get_refresh_token_from_request(request: Request) -> str | None:
    """Get refresh token from cookie or Authorization header."""
    token = request.cookies.get(settings.REFRESH_TOKEN_COOKIE_NAME)
    if token:
        return token

    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        return auth_header.split(" ", 1)[1]
    return None
