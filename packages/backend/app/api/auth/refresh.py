"""
刷新 Token API
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request
from pydantic import BaseModel

from app.core.auth import verify_token, create_access_token

router = APIRouter()


class RefreshResponse(BaseModel):
    """刷新响应"""
    access_token: str
    token_type: str = "bearer"


@router.post("/refresh", response_model=RefreshResponse)
async def refresh_token(request: Request):
    """
    刷新 access token
    
    说明：
    - 客户端需要在请求头中携带当前（可能已过期）的 token
    - 或者通过 HttpOnly Cookie 携带 refresh token（推荐）
    - 返回新的 access token
    
    Returns:
        新的 access_token
        
    Raises:
        401: Token 无效或已过期
    """
    # 方案 1：从 Authorization header 获取（允许过期）
    auth_header = request.headers.get("Authorization")
    
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid authorization header"
        )
    
    token = auth_header.split(" ")[1]
    
    try:
        # 验证 token（即使过期也能解析出用户信息）
        payload = verify_token(token)
        user_id = payload["user_id"]
        username = payload.get("username", "")
        email = payload.get("email", "")
        
        # 生成新的 access token
        new_token = create_access_token(
            user_id=user_id,
            username=username,
            email=email
        )
        
        return RefreshResponse(access_token=new_token)
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid or expired refresh token: {str(e)}"
        )

