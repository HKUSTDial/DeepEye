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
from app.sandbox import sandbox_manager
from deepeye.utils.logger import logger


async def initialize_checkpointer() -> None:
    if not settings.LANGGRAPH_CHECKPOINTER_AUTO_SETUP:
        logger.info("Skipping LangGraph checkpointer setup.")
        return

    try:
        async with AsyncPostgresSaver.from_conn_string(settings.POSTGRES_STATE_URL) as checkpointer:
            await checkpointer.setup()
        logger.info("LangGraph Checkpointer DB initialized.")
    except Exception as e:
        logger.error(f"Error initializing LangGraph Checkpointer: {e}")


def start_sandbox_cleanup() -> None:
    if not settings.SANDBOX_CLEANUP_ENABLED:
        logger.info("Skipping sandbox cleanup task startup.")
        return
    if settings.DOCKER_CONTROL_MODE == "remote":
        logger.info("Skipping local sandbox cleanup startup in remote Docker control mode.")
        return

    sandbox_manager.start_cleanup_task()
    logger.info("Sandbox cleanup task started.")


async def stop_sandbox_cleanup() -> None:
    if not settings.SANDBOX_CLEANUP_ENABLED:
        return
    if settings.DOCKER_CONTROL_MODE == "remote":
        return

    await sandbox_manager.stop_cleanup_task()
    await sandbox_manager.cleanup_all()
    logger.info("Sandbox cleanup completed.")


@asynccontextmanager
async def lifespan(_: FastAPI):
    run_startup_warmup(component="api")
    await initialize_checkpointer()
    start_sandbox_cleanup()

    yield

    await stop_sandbox_cleanup()


def create_app() -> FastAPI:
    app = FastAPI(title="DeepEye API", version="0.1.0", lifespan=lifespan)

    cors_origins = [str(origin).rstrip("/") for origin in settings.BACKEND_CORS_ORIGINS]
    cors_origins = [origin for origin in cors_origins if origin != "*"]
    if not cors_origins:
        cors_origins = ["http://localhost:5173", "http://127.0.0.1:5173"]
        logger.warning(
            "BACKEND_CORS_ORIGINS contains wildcard or is empty. Falling back to localhost origins."
        )

    # 注意：在 FastAPI 中，后添加的中间件会包裹在先添加的中间件“外面”。
    # 我们希望 CORS 在最外层，所以先添加业务中间件，后添加 CORS 中间件。
    app.middleware("http")(auth_middleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.error(f"Unhandled exception: {exc}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "Internal server error"},
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"detail": "Validation error", "errors": exc.errors()},
        )

    app.include_router(auth_router)
    app.include_router(public_router)
    app.include_router(v1_router)

    @app.get("/")
    async def root():
        return {"message": "DeepEye API is running"}

    @app.get("/health")
    async def health_check():
        return {"status": "ok"}

    return app


app = create_app()
