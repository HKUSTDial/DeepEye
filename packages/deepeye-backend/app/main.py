"""FastAPI application main file."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import auth, nodes, workflow
from app.config import settings

# Import deepeye-core nodes to ensure they are registered
# All nodes are automatically registered via @register_node decorator
# when deepeye.nodes module is imported
try:
    import deepeye.nodes  # noqa: F401  # 导入以触发节点自动注册
except ImportError:
    # If deepeye-core is not available, continue without nodes
    pass

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    debug=settings.DEBUG,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
)

# CORS middleware
if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.BACKEND_CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Register API routes
app.include_router(auth.router, prefix=settings.API_V1_PREFIX)
app.include_router(workflow.router, prefix=settings.API_V1_PREFIX)
app.include_router(nodes.router, prefix=settings.API_V1_PREFIX)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "DeepEye API",
        "version": settings.VERSION,
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}
