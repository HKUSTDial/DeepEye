"""
认证 API
"""
from fastapi import APIRouter
from . import login, register, refresh

router = APIRouter(prefix="/api/auth", tags=["auth"])

# 注册子路由
router.include_router(login.router)
router.include_router(register.router)
router.include_router(refresh.router)

__all__ = ["router"]

