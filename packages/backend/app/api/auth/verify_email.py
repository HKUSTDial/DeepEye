"""Email verification APIs."""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.auth.schemas import GenericMessageResponse, VerifyEmailConfirmRequest, VerifyEmailRequest
from app.core.auth import ACTION_TOKEN_PURPOSE_VERIFY_EMAIL, create_action_token, hash_token
from app.core.config import settings
from app.db.session import get_db
from app.models import User
from app.repositories import AuthActionTokenRepository, UserEmailVerificationRepository
from app.auth.services.audit import log_auth_event
from app.auth.services.email import send_verification_email

router = APIRouter()

_REQUEST_ACCEPTED_MESSAGE = "If the email exists, a verification message has been sent."


@router.post("/verify-email/request", response_model=GenericMessageResponse)
async def request_email_verification(
    payload: VerifyEmailRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> GenericMessageResponse:
    """Request email verification token."""
    normalized_email = payload.email.strip().lower()
    debug_token: str | None = None
    user = db.query(User).filter(func.lower(User.email) == normalized_email).first()

    if user:
        verified_repo = UserEmailVerificationRepository(db)
        already_verified = verified_repo.is_verified(user.id)
        if not already_verified:
            token_repo = AuthActionTokenRepository(db)
            token_repo.revoke_active_for_user(user.id, ACTION_TOKEN_PURPOSE_VERIFY_EMAIL)
            token, token_hash, expires_at = create_action_token(
                expires_in_minutes=settings.EMAIL_VERIFICATION_TOKEN_EXPIRE_MINUTES,
            )
            client_ip = request.client.host if request.client and request.client.host else None
            token_repo.issue(
                user_id=user.id,
                purpose=ACTION_TOKEN_PURPOSE_VERIFY_EMAIL,
                token_hash=token_hash,
                expires_at=expires_at,
                requested_by_ip=client_ip,
                user_agent=request.headers.get("user-agent"),
            )
            send_verification_email(user.email, token)
            if settings.AUTH_DEBUG_RETURN_ACTION_TOKEN:
                debug_token = token
            log_auth_event(
                db,
                event_type="verify_email.request",
                success=True,
                user_id=user.id,
                email=user.email,
                detail="verification_requested",
                request=request,
            )
        else:
            log_auth_event(
                db,
                event_type="verify_email.request",
                success=True,
                user_id=user.id,
                email=user.email,
                detail="already_verified",
                request=request,
            )
    else:
        log_auth_event(
            db,
            event_type="verify_email.request",
            success=False,
            email=normalized_email,
            detail="email_not_found",
            request=request,
        )

    return GenericMessageResponse(message=_REQUEST_ACCEPTED_MESSAGE, debug_token=debug_token)


@router.post("/verify-email/confirm", response_model=GenericMessageResponse)
async def confirm_email_verification(
    payload: VerifyEmailConfirmRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> GenericMessageResponse:
    """Consume verification token and mark email as verified."""
    token_value = payload.token.strip()
    if not token_value:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid verification token")

    token_repo = AuthActionTokenRepository(db)
    client_ip = request.client.host if request.client and request.client.host else None
    consumed = token_repo.consume(
        purpose=ACTION_TOKEN_PURPOSE_VERIFY_EMAIL,
        token_hash=hash_token(token_value),
        consumed_by_ip=client_ip,
    )
    if not consumed:
        log_auth_event(
            db,
            event_type="verify_email.confirm",
            success=False,
            detail="invalid_or_expired_token",
            request=request,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification token",
        )

    user = db.query(User).filter(User.id == consumed.user_id).first()
    if not user:
        log_auth_event(
            db,
            event_type="verify_email.confirm",
            success=False,
            detail="user_not_found",
            request=request,
        )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid verification token")

    UserEmailVerificationRepository(db).mark_verified(user.id)
    log_auth_event(
        db,
        event_type="verify_email.confirm",
        success=True,
        user_id=user.id,
        email=user.email,
        detail="email_verified",
        request=request,
    )
    return GenericMessageResponse(message="Email verified successfully.")
