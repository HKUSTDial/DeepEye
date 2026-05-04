"""Login API."""

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import func
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr

from app.api.auth.cookies import set_auth_cookies
from app.api.auth.schemas import AuthResponse, AuthUser
from app.core.auth import create_access_token, create_refresh_token, hash_token, verify_password
from app.core.config import settings
from app.core.login_throttle import clear_failures, is_limited, record_failure
from app.db.session import get_db
from app.models.user import User
from app.repositories import RefreshTokenRepository, UserEmailVerificationRepository
from app.auth.services.audit import log_auth_event

router = APIRouter()


class LoginRequest(BaseModel):
    """登录请求"""
    email: EmailStr
    password: str


@router.post("/login", response_model=AuthResponse)
async def login(
    data: LoginRequest,
    response: Response,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    用户登录
    
    Args:
        data: 登录信息（email + password）
        db: 数据库会话
        
    Returns:
        access_token + 用户信息
        
    Raises:
        401: 邮箱或密码错误
    """
    normalized_email = data.email.strip().lower()
    client_ip = request.client.host if request.client and request.client.host else "unknown"
    throttle_keys = [f"email:{normalized_email}", f"ip:{client_ip}"]

    for key in throttle_keys:
        limited, retry_after = is_limited(
            key,
            max_attempts=settings.AUTH_LOGIN_MAX_ATTEMPTS,
            window_seconds=settings.AUTH_LOGIN_WINDOW_SECONDS,
        )
        if limited:
            log_auth_event(
                db,
                event_type="login",
                success=False,
                email=normalized_email,
                detail=f"rate_limited:{key}",
                request=request,
            )
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Too many login attempts. Try again in {retry_after} seconds.",
            )

    # 1. 查询用户（大小写不敏感）
    user = db.query(User).filter(func.lower(User.email) == normalized_email).first()
    if not user:
        for key in throttle_keys:
            record_failure(key, window_seconds=settings.AUTH_LOGIN_WINDOW_SECONDS)
        log_auth_event(
            db,
            event_type="login",
            success=False,
            email=normalized_email,
            detail="email_not_found",
            request=request,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    # 2. 验证密码
    if not verify_password(data.password, user.hashed_password):
        for key in throttle_keys:
            record_failure(key, window_seconds=settings.AUTH_LOGIN_WINDOW_SECONDS)
        log_auth_event(
            db,
            event_type="login",
            success=False,
            user_id=user.id,
            email=user.email,
            detail="invalid_password",
            request=request,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    # 3. 检查用户状态
    if not user.is_active:
        log_auth_event(
            db,
            event_type="login",
            success=False,
            user_id=user.id,
            email=user.email,
            detail="inactive_user",
            request=request,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )

    is_email_verified = UserEmailVerificationRepository(db).is_verified(user.id)
    if settings.REQUIRE_EMAIL_VERIFICATION and not is_email_verified:
        log_auth_event(
            db,
            event_type="login",
            success=False,
            user_id=user.id,
            email=user.email,
            detail="email_not_verified",
            request=request,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email not verified",
        )

    for key in throttle_keys:
        clear_failures(key)
    
    # 4. 生成 JWT token
    access_token = create_access_token(
        user_id=user.id,
        username=user.username,
        email=user.email
    )
    refresh_token, refresh_jti, refresh_expires_at = create_refresh_token(
        user_id=user.id,
        username=user.username,
        email=user.email,
    )
    RefreshTokenRepository(db).issue(
        user_id=user.id,
        token_jti=refresh_jti,
        token_hash=hash_token(refresh_token),
        expires_at=refresh_expires_at,
        created_by_ip=client_ip,
        user_agent=request.headers.get("user-agent"),
    )
    set_auth_cookies(response, access_token, refresh_token)
    log_auth_event(
        db,
        event_type="login",
        success=True,
        user_id=user.id,
        email=user.email,
        detail="login_success",
        request=request,
    )
    
    # 5. 返回 token 和用户信息
    return AuthResponse(
        access_token=access_token,
        user=AuthUser(
            id=str(user.id),
            email=user.email,
            username=user.username,
            is_superuser=user.is_superuser,
            is_email_verified=is_email_verified,
        ),
    )
