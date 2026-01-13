"""
沙箱相关 API
"""
from fastapi import APIRouter
from . import management, files

router = APIRouter(prefix="/sandbox", tags=["sandbox"])

# 注册子路由
router.include_router(management.router)    # /api/v1/sandbox (沙箱管理)
router.include_router(files.router)         # /api/v1/sandbox/files (文件操作)

__all__ = ["router"]

