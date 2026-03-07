from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from app.api.auth import router as auth_router
from app.api.public import router as public_router
from app.api.v1 import router as v1_router
from app.core.config import settings
from app.core.middleware import auth_middleware
from app.core.warmup import run_startup_warmup
from app.db.session import engine
from app.models import Base
from app.sandbox import sandbox_manager
from deepeye.utils.logger import logger

# 启动时创建所有表
Base.metadata.create_all(bind=engine)


@asynccontextmanager
async def lifespan(_: FastAPI):
    run_startup_warmup(component="api")

    # Startup: 初始化 LangGraph Checkpointer
    try:
        async with AsyncPostgresSaver.from_conn_string(settings.POSTGRES_STATE_URL) as checkpointer:
            await checkpointer.setup()
        logger.info("LangGraph Checkpointer DB initialized.")
    except Exception as e:
        logger.error(f"Error initializing LangGraph Checkpointer: {e}")
    
    # Startup: 启动 Sandbox cleanup task
    sandbox_manager.start_cleanup_task()
    logger.info("Sandbox cleanup task started.")
    
    yield
    
    # Shutdown: 停止 cleanup task 并清理所有 sandboxes
    await sandbox_manager.stop_cleanup_task()
    await sandbox_manager.cleanup_all()
    logger.info("Sandbox cleanup completed.")


app = FastAPI(title="DeepEye API", version="0.1.0", lifespan=lifespan)

_cors_origins = [str(origin).rstrip("/") for origin in settings.BACKEND_CORS_ORIGINS]
_cors_origins = [origin for origin in _cors_origins if origin != "*"]
if not _cors_origins:
    _cors_origins = ["http://localhost:5173", "http://127.0.0.1:5173"]
    logger.warning("BACKEND_CORS_ORIGINS contains wildcard or is empty. Falling back to localhost origins.")

# ⭐ 全局鉴权中间件
# 注意：在 FastAPI 中，后添加的中间件会包裹在先添加的中间件“外面”。
# 我们希望 CORS 在最外层，所以先添加业务中间件，后添加 CORS 中间件。
app.middleware("http")(auth_middleware)

# CORS 中间件 (最外层)
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 全局异常处理器 - 确保所有错误都返回 JSON 并包含 CORS headers
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """处理所有未捕获的异常"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error"},
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """处理请求验证错误"""
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": "Validation error",
            "errors": exc.errors()
        }
    )


# 公开路由（不需要鉴权）
app.include_router(auth_router)      # /api/auth/*
app.include_router(public_router)    # /api/public/*

# 业务路由 v1（需要鉴权）
app.include_router(v1_router)        # /api/v1/*


@app.get("/")
async def root():
    return {"message": "DeepEye API is running"}


@app.get("/health")
async def health_check():
    return {"status": "ok"}
