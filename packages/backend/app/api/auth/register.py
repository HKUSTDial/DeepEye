"""Register API."""

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import func
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from pydantic import BaseModel, EmailStr, Field

from app.api.auth.cookies import set_auth_cookies
from app.api.auth.schemas import AuthResponse, AuthUser
from app.core.auth import (
    ACTION_TOKEN_PURPOSE_VERIFY_EMAIL,
    create_access_token,
    create_action_token,
    create_refresh_token,
    get_password_hash,
    hash_token,
    validate_password_strength,
)
from app.core.config import settings
from app.db.session import get_db
from app.models.user import User
from app.repositories import AuthActionTokenRepository, RefreshTokenRepository
from app.auth.services.audit import log_auth_event
from app.auth.services.email import send_verification_email

router = APIRouter()


class RegisterRequest(BaseModel):
    """注册请求"""
    email: EmailStr
    username: str = Field(..., min_length=2, max_length=50)
    password: str = Field(..., min_length=8, max_length=64)


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def register(
    data: RegisterRequest,
    response: Response,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    用户注册
    
    Args:
        data: 注册信息（email + username + password）
        db: 数据库会话
        
    Returns:
        access_token + 用户信息
        
    Raises:
        400: 邮箱已被注册
    """
    normalized_email = data.email.strip().lower()
    normalized_username = data.username.strip()
    if len(normalized_username) < 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username must be at least 2 non-space characters",
        )

    try:
        validate_password_strength(data.password)
    except ValueError as exc:
        log_auth_event(
            db,
            event_type="register",
            success=False,
            email=normalized_email,
            detail=str(exc),
            request=request,
        )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    # 1. 检查邮箱是否已存在（大小写不敏感）
    existing_user = db.query(User).filter(func.lower(User.email) == normalized_email).first()
    if existing_user:
        log_auth_event(
            db,
            event_type="register",
            success=False,
            email=normalized_email,
            detail="email_already_registered",
            request=request,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # 2. 创建新用户
    hashed_password = get_password_hash(data.password)
    new_user = User(
        email=normalized_email,
        username=normalized_username,
        hashed_password=hashed_password,
        is_active=True,
        is_superuser=False
    )
    
    try:
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
    except IntegrityError:
        db.rollback()
        log_auth_event(
            db,
            event_type="register",
            success=False,
            email=normalized_email,
            detail="integrity_error_email_exists",
            request=request,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # 3. 生成 JWT token
    access_token = create_access_token(
        user_id=new_user.id,
        username=new_user.username,
        email=new_user.email
    )
    refresh_token, refresh_jti, refresh_expires_at = create_refresh_token(
        user_id=new_user.id,
        username=new_user.username,
        email=new_user.email,
    )
    client_ip = request.client.host if request.client and request.client.host else None
    RefreshTokenRepository(db).issue(
        user_id=new_user.id,
        token_jti=refresh_jti,
        token_hash=hash_token(refresh_token),
        expires_at=refresh_expires_at,
        created_by_ip=client_ip,
        user_agent=request.headers.get("user-agent"),
    )

    verify_token, verify_token_hash, verify_expires_at = create_action_token(
        expires_in_minutes=settings.EMAIL_VERIFICATION_TOKEN_EXPIRE_MINUTES,
    )
    AuthActionTokenRepository(db).revoke_active_for_user(new_user.id, ACTION_TOKEN_PURPOSE_VERIFY_EMAIL)
    AuthActionTokenRepository(db).issue(
        user_id=new_user.id,
        purpose=ACTION_TOKEN_PURPOSE_VERIFY_EMAIL,
        token_hash=verify_token_hash,
        expires_at=verify_expires_at,
        requested_by_ip=client_ip,
        user_agent=request.headers.get("user-agent"),
    )
    send_verification_email(new_user.email, verify_token)

    set_auth_cookies(response, access_token, refresh_token)
    log_auth_event(
        db,
        event_type="register",
        success=True,
        user_id=new_user.id,
        email=new_user.email,
        detail="register_success",
        request=request,
    )
    
    # 4. 返回 token 和用户信息
    return AuthResponse(
        access_token=access_token,
        user=AuthUser(
            id=str(new_user.id),
            email=new_user.email,
            username=new_user.username,
            is_superuser=new_user.is_superuser,
            is_email_verified=False,
        ),
    )
