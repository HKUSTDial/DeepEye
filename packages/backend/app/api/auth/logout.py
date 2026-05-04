"""Logout API."""

import uuid

from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy.orm import Session

from app.api.auth.cookies import clear_auth_cookies
from app.api.auth.token_utils import get_refresh_token_from_request
from app.core.auth import verify_token
from app.db.session import get_db
from app.repositories import RefreshTokenRepository
from app.auth.services.audit import log_auth_event

router = APIRouter()


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
) -> Response:
    """Clear auth cookies."""
    user_id: uuid.UUID | None = None
    detail = "logout_cookie_clear_only"
    token = get_refresh_token_from_request(request)
    if token:
        try:
            payload = verify_token(token, expected_type="refresh", allow_expired=True)
            user_id = uuid.UUID(payload["user_id"])
            token_jti = uuid.UUID(payload["jti"])
            revoked = RefreshTokenRepository(db).revoke_by_jti(user_id, token_jti)
            detail = "logout_refresh_revoked" if revoked else "logout_refresh_already_revoked"
        except Exception:
            # Best effort: logout should still clear cookies even if token parse fails.
            detail = "logout_token_parse_failed"

    clear_auth_cookies(response)
    log_auth_event(
        db,
        event_type="logout",
        success=True,
        user_id=user_id,
        detail=detail,
        request=request,
    )
    response.status_code = status.HTTP_204_NO_CONTENT
    return response
