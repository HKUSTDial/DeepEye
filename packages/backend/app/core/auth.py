"""
JWT 认证工具
"""
from datetime import datetime, timedelta, timezone
from typing import Optional
import uuid

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

# JWT 配置
SECRET_KEY = settings.JWT_SECRET_KEY
ALGORITHM = settings.JWT_ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES

# 密码加密
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def create_access_token(user_id: uuid.UUID, username: str, email: str) -> str:
    """
    创建 JWT access token
    
    Args:
        user_id: 用户 ID
        username: 用户名
        email: 用户邮箱
        
    Returns:
        JWT token string
    """
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "user_id": str(user_id),
        "username": username,
        "email": email,
        "exp": expire,
        "iat": datetime.now(timezone.utc)
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def verify_token(token: str) -> dict:
    """
    验证 JWT token
    
    Args:
        token: JWT token string
        
    Returns:
        Decoded payload
        
    Raises:
        JWTError: Token 无效或已过期
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError as e:
        raise ValueError(f"Invalid token: {str(e)}")


def _truncate_password(password: str, max_bytes: int = 72) -> str:
    """
    截断密码到指定字节数（bcrypt 限制）
    
    Args:
        password: 原始密码
        max_bytes: 最大字节数（默认 72）
        
    Returns:
        截断后的密码
    """
    password_bytes = password.encode('utf-8')
    if len(password_bytes) <= max_bytes:
        return password
    # 截断到 max_bytes，确保不破坏 UTF-8 字符
    return password_bytes[:max_bytes].decode('utf-8', errors='ignore')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    验证密码
    
    Args:
        plain_password: 明文密码
        hashed_password: 哈希后的密码
        
    Returns:
        True if 密码匹配, False otherwise
    """
    truncated = _truncate_password(plain_password)
    return pwd_context.verify(truncated, hashed_password)


def get_password_hash(password: str) -> str:
    """
    密码加密（自动截断到 72 字节）
    
    Args:
        password: 明文密码
        
    Returns:
        哈希后的密码
    """
    truncated = _truncate_password(password)
    return pwd_context.hash(truncated)

