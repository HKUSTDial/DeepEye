"""
FastAPI 依赖注入辅助函数
"""
from typing import Annotated
import uuid

from fastapi import Request, HTTPException, Depends


def get_current_user_id_from_state(request: Request) -> uuid.UUID:
    """
    从 request.state 获取当前用户 ID
    
    需要配合全局 auth_middleware 使用
    中间件会自动将 user_id 注入到 request.state
    
    Args:
        request: FastAPI Request 对象
        
    Returns:
        当前用户的 UUID
        
    Raises:
        HTTPException: 如果 user_id 不存在（理论上不会发生，因为中间件会拦截）
        
    Usage:
        @router.get("/example")
        async def example(user_id: CurrentUserId):
            # user_id 自动注入
            pass
    """
    if not hasattr(request.state, "user_id"):
        raise HTTPException(
            status_code=401,
            detail="User ID not found in request state. Auth middleware may not be configured."
        )
    return request.state.user_id


def get_current_username_from_state(request: Request) -> str:
    """
    从 request.state 获取当前用户名
    
    Args:
        request: FastAPI Request 对象
        
    Returns:
        当前用户的用户名
    """
    if not hasattr(request.state, "username"):
        return ""
    return request.state.username


# 类型别名：简化代码
CurrentUserId = Annotated[uuid.UUID, Depends(get_current_user_id_from_state)]
CurrentUsername = Annotated[str, Depends(get_current_username_from_state)]

