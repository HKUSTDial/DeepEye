"""Runtime inspection endpoints."""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from app.core.config import settings
from app.runtime.services.metrics import runtime_metrics

router = APIRouter(prefix="/system", tags=["system"])


class RuntimeSummaryResponse(BaseModel):
    docker_control_mode: str
    docker_control_url: str
    sandbox_cleanup_enabled: bool
    preview_runtime_ttl_seconds: int
    preview_runtime_max_containers: int
    metrics: dict


@router.get("/runtime", response_model=RuntimeSummaryResponse)
async def get_runtime_summary():
    return RuntimeSummaryResponse(
        docker_control_mode=settings.DOCKER_CONTROL_MODE,
        docker_control_url=settings.DOCKER_CONTROL_URL,
        sandbox_cleanup_enabled=settings.SANDBOX_CLEANUP_ENABLED,
        preview_runtime_ttl_seconds=settings.PREVIEW_RUNTIME_TTL_SECONDS,
        preview_runtime_max_containers=settings.PREVIEW_RUNTIME_MAX_CONTAINERS,
        metrics=runtime_metrics.snapshot(),
    )
