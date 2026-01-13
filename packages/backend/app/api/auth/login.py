"""
登录 API
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr

from app.db.session import get_db
from app.models.user import User
from app.core.auth import verify_password, create_access_token

router = APIRouter()


class LoginRequest(BaseModel):
    """登录请求"""
    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    """登录响应"""
    access_token: str
    token_type: str = "bearer"
    user: dict


@router.post("/login", response_model=LoginResponse)
async def login(
    data: LoginRequest,
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
    # 1. 查询用户
    user = db.query(User).filter(User.email == data.email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    # 2. 验证密码
    if not verify_password(data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    # 3. 检查用户状态
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )
    
    # 4. 生成 JWT token
    access_token = create_access_token(
        user_id=user.id,
        username=user.username,
        email=user.email
    )
    
    # 5. 返回 token 和用户信息
    return LoginResponse(
        access_token=access_token,
        user={
            "id": str(user.id),
            "email": user.email,
            "username": user.username,
            "is_superuser": user.is_superuser
        }
    )

