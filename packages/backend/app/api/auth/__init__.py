"""Auth API."""

from fastapi import APIRouter
from . import login, logout, password_reset, refresh, register, verify_email

router = APIRouter(prefix="/api/auth", tags=["auth"])

# 注册子路由
router.include_router(login.router)
router.include_router(register.router)
router.include_router(refresh.router)
router.include_router(logout.router)
router.include_router(verify_email.router)
router.include_router(password_reset.router)

__all__ = ["router"]
