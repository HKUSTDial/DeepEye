"""Password reset APIs."""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.auth.schemas import GenericMessageResponse, PasswordResetConfirmRequest, PasswordResetRequest
from app.core.auth import (
    ACTION_TOKEN_PURPOSE_PASSWORD_RESET,
    create_action_token,
    get_password_hash,
    hash_token,
    validate_password_strength,
)
from app.core.config import settings
from app.db.session import get_db
from app.models import User
from app.repositories import AuthActionTokenRepository, RefreshTokenRepository
from app.auth.services.audit import log_auth_event
from app.auth.services.email import send_password_reset_email

router = APIRouter()

_REQUEST_ACCEPTED_MESSAGE = "If the email exists, a password reset message has been sent."


@router.post("/password-reset/request", response_model=GenericMessageResponse)
async def request_password_reset(
    payload: PasswordResetRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> GenericMessageResponse:
    """Request password reset token."""
    normalized_email = payload.email.strip().lower()
    debug_token: str | None = None
    user = db.query(User).filter(func.lower(User.email) == normalized_email).first()

    if user and user.is_active:
        token_repo = AuthActionTokenRepository(db)
        token_repo.revoke_active_for_user(user.id, ACTION_TOKEN_PURPOSE_PASSWORD_RESET)
        token, token_hash, expires_at = create_action_token(
            expires_in_minutes=settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES,
        )
        client_ip = request.client.host if request.client and request.client.host else None
        token_repo.issue(
            user_id=user.id,
            purpose=ACTION_TOKEN_PURPOSE_PASSWORD_RESET,
            token_hash=token_hash,
            expires_at=expires_at,
            requested_by_ip=client_ip,
            user_agent=request.headers.get("user-agent"),
        )
        send_password_reset_email(user.email, token)
        if settings.AUTH_DEBUG_RETURN_ACTION_TOKEN:
            debug_token = token
        log_auth_event(
            db,
            event_type="password_reset.request",
            success=True,
            user_id=user.id,
            email=user.email,
            detail="password_reset_requested",
            request=request,
        )
    else:
        log_auth_event(
            db,
            event_type="password_reset.request",
            success=False,
            email=normalized_email,
            detail="email_not_found_or_inactive",
            request=request,
        )

    return GenericMessageResponse(message=_REQUEST_ACCEPTED_MESSAGE, debug_token=debug_token)


@router.post("/password-reset/confirm", response_model=GenericMessageResponse)
async def confirm_password_reset(
    payload: PasswordResetConfirmRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> GenericMessageResponse:
    """Consume reset token, update password, revoke refresh sessions."""
    token_value = payload.token.strip()
    if not token_value:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid password reset token")

    try:
        validate_password_strength(payload.new_password)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    token_repo = AuthActionTokenRepository(db)
    client_ip = request.client.host if request.client and request.client.host else None
    consumed = token_repo.consume(
        purpose=ACTION_TOKEN_PURPOSE_PASSWORD_RESET,
        token_hash=hash_token(token_value),
        consumed_by_ip=client_ip,
    )
    if not consumed:
        log_auth_event(
            db,
            event_type="password_reset.confirm",
            success=False,
            detail="invalid_or_expired_token",
            request=request,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired password reset token",
        )

    user = db.query(User).filter(User.id == consumed.user_id).first()
    if not user or not user.is_active:
        log_auth_event(
            db,
            event_type="password_reset.confirm",
            success=False,
            detail="user_not_found_or_inactive",
            request=request,
        )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid password reset token")

    user.hashed_password = get_password_hash(payload.new_password)
    db.add(user)
    db.commit()
    db.refresh(user)

    revoked_count = RefreshTokenRepository(db).revoke_all_for_user(user.id)
    log_auth_event(
        db,
        event_type="password_reset.confirm",
        success=True,
        user_id=user.id,
        email=user.email,
        detail=f"password_reset_success;refresh_revoked={revoked_count}",
        request=request,
    )
    return GenericMessageResponse(message="Password has been reset successfully.")
