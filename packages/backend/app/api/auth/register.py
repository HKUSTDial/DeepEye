"""
注册 API
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from pydantic import BaseModel, EmailStr, Field

from app.db.session import get_db
from app.models.user import User
from app.core.auth import get_password_hash, create_access_token

router = APIRouter()


class RegisterRequest(BaseModel):
    """注册请求"""
    email: EmailStr
    username: str = Field(..., min_length=2, max_length=50)
    password: str = Field(..., min_length=6, max_length=64)  # 保守限制，bcrypt 实际限制 72 字节


class RegisterResponse(BaseModel):
    """注册响应"""
    access_token: str
    token_type: str = "bearer"
    user: dict


@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
async def register(
    data: RegisterRequest,
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
    # 1. 检查邮箱是否已存在
    existing_user = db.query(User).filter(User.email == data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # 2. 创建新用户
    hashed_password = get_password_hash(data.password)
    new_user = User(
        email=data.email,
        username=data.username,
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
    
    # 4. 返回 token 和用户信息
    return RegisterResponse(
        access_token=access_token,
        user={
            "id": str(new_user.id),
            "email": new_user.email,
            "username": new_user.username,
            "is_superuser": new_user.is_superuser
        }
    )

