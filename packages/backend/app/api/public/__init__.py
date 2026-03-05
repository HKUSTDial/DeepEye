"""
公开 API（不需要鉴权）
"""
from fastapi import APIRouter
from . import health

router = APIRouter(prefix="/api/public", tags=["public"])

# 注册子路由
router.include_router(health.router)

__all__ = ["router"]
