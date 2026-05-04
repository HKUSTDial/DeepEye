"""Refresh token API."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from app.api.auth.cookies import set_auth_cookies
from app.api.auth.schemas import RefreshResponse
from app.api.auth.token_utils import get_refresh_token_from_request
from app.core.auth import create_access_token, create_refresh_token, hash_token, verify_token
from app.core.config import settings
from app.db.session import get_db
from app.models.user import User
from app.repositories import RefreshTokenRepository, UserEmailVerificationRepository
from app.auth.services.audit import log_auth_event

router = APIRouter()


@router.post("/refresh", response_model=RefreshResponse)
async def refresh_token(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    """Issue a new token pair from a valid refresh token."""
    token = get_refresh_token_from_request(request)

    if not token:
        log_auth_event(
            db,
            event_type="refresh",
            success=False,
            detail="missing_refresh_token",
            request=request,
        )
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing refresh token")

    try:
        payload = verify_token(token, expected_type="refresh")
        user_id = uuid.UUID(payload["user_id"])
        token_jti = uuid.UUID(payload["jti"])
    except Exception as exc:
        log_auth_event(
            db,
            event_type="refresh",
            success=False,
            detail="invalid_refresh_token",
            request=request,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        ) from exc

    token_repo = RefreshTokenRepository(db)
    token_record = token_repo.get_active_by_jti(user_id, token_jti)
    if not token_record:
        log_auth_event(
            db,
            event_type="refresh",
            success=False,
            user_id=user_id,
            detail="token_revoked_or_expired",
            request=request,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token revoked or expired",
        )
    if token_record.token_hash != hash_token(token):
        log_auth_event(
            db,
            event_type="refresh",
            success=False,
            user_id=user_id,
            detail="token_hash_mismatch",
            request=request,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token mismatch",
        )

    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.is_active:
        log_auth_event(
            db,
            event_type="refresh",
            success=False,
            user_id=user_id,
            detail="user_not_found_or_inactive",
            request=request,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )

    if settings.REQUIRE_EMAIL_VERIFICATION and not UserEmailVerificationRepository(db).is_verified(user.id):
        log_auth_event(
            db,
            event_type="refresh",
            success=False,
            user_id=user.id,
            email=user.email,
            detail="email_not_verified",
            request=request,
        )
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Email not verified")

    new_access_token = create_access_token(
        user_id=user.id,
        username=user.username,
        email=user.email,
    )
    new_refresh_token, new_refresh_jti, new_refresh_expires_at = create_refresh_token(
        user_id=user.id,
        username=user.username,
        email=user.email,
    )
    client_ip = request.client.host if request.client and request.client.host else None
    token_repo.rotate(
        token_record,
        new_token_jti=new_refresh_jti,
        new_token_hash=hash_token(new_refresh_token),
        new_expires_at=new_refresh_expires_at,
        created_by_ip=client_ip,
        user_agent=request.headers.get("user-agent"),
    )
    set_auth_cookies(response, new_access_token, new_refresh_token)
    log_auth_event(
        db,
        event_type="refresh",
        success=True,
        user_id=user.id,
        email=user.email,
        detail="refresh_success",
        request=request,
    )
    return RefreshResponse(access_token=new_access_token)
