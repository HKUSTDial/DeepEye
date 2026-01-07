"""
业务 API v1 (需要鉴权)
"""
from fastapi import APIRouter
from . import sessions, chat, datasources, workflows, workflow_templates, workflow_files, workflow_nodes, knowledge_bases
from .sandbox import router as sandbox_router

router = APIRouter(prefix="/api/v1", tags=["v1"])

# 注册子路由
router.include_router(sessions.router)      # /api/v1/sessions
router.include_router(chat.router)          # /api/v1/chat
router.include_router(datasources.router)   # /api/v1/datasources
router.include_router(workflows.router)     # /api/v1/workflows
router.include_router(workflow_templates.router)  # /api/v1/workflow-templates
router.include_router(workflow_files.router)      # /api/v1/workflow-files
router.include_router(workflow_nodes.router)      # /api/v1/workflow-nodes
router.include_router(knowledge_bases.router)     # /api/v1/knowledge-bases
router.include_router(sandbox_router)       # /api/v1/sandbox

__all__ = ["router"]

