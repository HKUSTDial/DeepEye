"""
业务 API v1 (需要鉴权)
"""
from fastapi import APIRouter

from . import chat, datasources, sessions, system, video, workflow_files, workflow_nodes, workflows
from .sandbox import router as sandbox_router

router = APIRouter(prefix="/api/v1", tags=["v1"])

# 注册子路由
router.include_router(sessions.router)      # /api/v1/sessions
router.include_router(chat.router)          # /api/v1/chat
router.include_router(datasources.router)   # /api/v1/datasources
router.include_router(workflows.router)     # /api/v1/workflows
router.include_router(workflow_files.router)      # /api/v1/workflow-files
router.include_router(workflow_nodes.router)      # /api/v1/workflow-nodes
router.include_router(video.router)         # /api/v1/video
router.include_router(system.router)        # /api/v1/system
router.include_router(sandbox_router)       # /api/v1/sandbox

__all__ = ["router"]
