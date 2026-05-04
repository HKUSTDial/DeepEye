from __future__ import annotations

import base64
import io
from contextlib import asynccontextmanager
from dataclasses import asdict, is_dataclass
from typing import Any

from fastapi import Depends, FastAPI, Header, HTTPException, status
from pydantic import BaseModel

from app.core.config import settings
from app.deploy.services.dashboard import dashboard_deployer
from app.deploy.services.video import video_deployer
from app.runtime.services.preview_manager import preview_runtime_manager
from app.sandbox import sandbox_manager


def _container_or_404(sandbox):
    container = getattr(sandbox, "container", None)
    if container is None:
        raise HTTPException(status_code=404, detail="Sandbox container not found")
    return container


def _serialize_container(container) -> dict[str, Any]:
    labels = dict(getattr(container, "labels", {}) or {})
    attrs = dict(getattr(container, "attrs", {}) or {})
    return {
        "name": getattr(container, "name", None),
        "status": getattr(container, "status", None),
        "labels": labels,
        "attrs": attrs,
    }


def _serialize_sandbox(sandbox) -> dict[str, Any]:
    container = getattr(sandbox, "container", None)
    return {
        "session_id": getattr(sandbox, "session_id", None),
        "container_name": getattr(sandbox, "container_name", None),
        "volume_name": getattr(sandbox, "volume_name", None),
        "is_created": bool(getattr(sandbox, "is_created", False)),
        "is_running": sandbox.is_running(),
        "container": _serialize_container(container) if container is not None else None,
    }


def _serialize_command_result(result) -> dict[str, Any]:
    if hasattr(result, "model_dump"):
        payload = result.model_dump()
    elif is_dataclass(result):
        payload = asdict(result)
    elif hasattr(result, "dict"):
        payload = result.dict()
    else:
        payload = {
            "stdout": getattr(result, "stdout", ""),
            "stderr": getattr(result, "stderr", ""),
            "exit_code": getattr(result, "exit_code", -1),
            "success": getattr(result, "success", False),
            "execution_time_ms": getattr(result, "execution_time_ms", 0),
        }
    return dict(payload)


def require_internal_api_key(
    x_internal_api_key: str | None = Header(default=None, alias="X-Internal-Api-Key"),
) -> None:
    expected = (settings.DOCKER_CONTROL_API_KEY or "").strip()
    if expected and x_internal_api_key != expected:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid internal API key")


class CommandRequest(BaseModel):
    command: str


class WriteFileRequest(BaseModel):
    path: str
    content_base64: str


class ContainerExecRequest(BaseModel):
    cmd: list[str] | str
    demux: bool = False
    workdir: str | None = None


class ContainerArchiveRequest(BaseModel):
    path: str
    archive_base64: str


class VideoDeployRequest(BaseModel):
    task_id: str
    session_id: str


class DashboardDeployRequest(BaseModel):
    task_id: str
    local_va_app_path: str | None = None
    source_archive_base64: str | None = None
    session_id: str | None = None


router_dependencies = [Depends(require_internal_api_key)]


@asynccontextmanager
async def lifespan(_: FastAPI):
    if settings.SANDBOX_CLEANUP_ENABLED:
        sandbox_manager.start_cleanup_task()
    if settings.PREVIEW_RUNTIME_CLEANUP_ENABLED:
        preview_runtime_manager.start_cleanup_task()
    yield
    if settings.SANDBOX_CLEANUP_ENABLED:
        await sandbox_manager.stop_cleanup_task()
    if settings.PREVIEW_RUNTIME_CLEANUP_ENABLED:
        await preview_runtime_manager.stop_cleanup_task()


app = FastAPI(title="DeepEye Runtime Control", version="0.1.0", lifespan=lifespan)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/internal/runtime-control/sandbox/sessions/{session_id}/ensure", dependencies=router_dependencies)
async def ensure_sandbox(session_id: str) -> dict[str, Any]:
    sandbox = await sandbox_manager.get_or_create_sandbox(session_id)
    return _serialize_sandbox(sandbox)


@app.get("/internal/runtime-control/sandbox/sessions/{session_id}", dependencies=router_dependencies)
async def get_sandbox(session_id: str) -> dict[str, Any]:
    sandbox = await sandbox_manager.get_sandbox(session_id)
    if sandbox is None:
        raise HTTPException(status_code=404, detail="Sandbox not found")
    return _serialize_sandbox(sandbox)


@app.get("/internal/runtime-control/sandbox/sessions/{session_id}/status", dependencies=router_dependencies)
async def get_sandbox_status(session_id: str) -> dict[str, Any]:
    return sandbox_manager.get_session_status(session_id)


@app.get("/internal/runtime-control/sandbox/stats", dependencies=router_dependencies)
async def get_sandbox_stats() -> dict[str, Any]:
    return sandbox_manager.get_stats()


@app.post("/internal/runtime-control/sandbox/sessions/{session_id}/exec", dependencies=router_dependencies)
async def exec_sandbox_command(session_id: str, payload: CommandRequest) -> dict[str, Any]:
    sandbox = await sandbox_manager.get_or_create_sandbox(session_id)
    result = await sandbox.exec_command(payload.command)
    return _serialize_command_result(result)


@app.post("/internal/runtime-control/sandbox/sessions/{session_id}/write-file", dependencies=router_dependencies)
async def write_sandbox_file(session_id: str, payload: WriteFileRequest) -> dict[str, str]:
    sandbox = await sandbox_manager.get_or_create_sandbox(session_id)
    await sandbox.write_file(payload.path, base64.b64decode(payload.content_base64))
    return {"status": "ok"}


@app.post("/internal/runtime-control/sandbox/sessions/{session_id}/start", dependencies=router_dependencies)
async def start_sandbox(session_id: str) -> dict[str, Any]:
    await sandbox_manager.start_session(session_id)
    sandbox = await sandbox_manager.get_or_create_sandbox(session_id)
    return _serialize_sandbox(sandbox)


@app.post("/internal/runtime-control/sandbox/sessions/{session_id}/stop", dependencies=router_dependencies)
async def stop_sandbox(session_id: str) -> dict[str, str]:
    await sandbox_manager.stop_session(session_id)
    return {"status": "ok"}


@app.delete("/internal/runtime-control/sandbox/sessions/{session_id}", dependencies=router_dependencies)
async def destroy_sandbox(session_id: str, delete_data: bool = False) -> dict[str, str]:
    await sandbox_manager.destroy_session(session_id, delete_data=delete_data)
    return {"status": "ok"}


@app.post("/internal/runtime-control/sandbox/sessions/{session_id}/sync", dependencies=router_dependencies)
async def sync_sandbox(session_id: str) -> dict[str, int]:
    reconnected = await sandbox_manager.sync_from_docker(session_id)
    return {"reconnected": reconnected}


@app.post("/internal/runtime-control/sandbox/cleanup/start", dependencies=router_dependencies)
async def start_cleanup() -> dict[str, str]:
    sandbox_manager.start_cleanup_task()
    return {"status": "ok"}


@app.post("/internal/runtime-control/sandbox/cleanup/stop", dependencies=router_dependencies)
async def stop_cleanup() -> dict[str, str]:
    await sandbox_manager.stop_cleanup_task()
    return {"status": "ok"}


@app.post("/internal/runtime-control/sandbox/cleanup/all", dependencies=router_dependencies)
async def cleanup_all() -> dict[str, str]:
    await sandbox_manager.cleanup_all()
    return {"status": "ok"}


@app.get("/internal/runtime-control/sandbox/sessions/{session_id}/container", dependencies=router_dependencies)
async def get_container_state(session_id: str) -> dict[str, Any]:
    sandbox = await sandbox_manager.get_sandbox(session_id)
    if sandbox is None:
        raise HTTPException(status_code=404, detail="Sandbox not found")
    container = _container_or_404(sandbox)
    container.reload()
    return _serialize_container(container)


@app.post("/internal/runtime-control/sandbox/sessions/{session_id}/container/exec", dependencies=router_dependencies)
async def exec_container(session_id: str, payload: ContainerExecRequest) -> dict[str, Any]:
    sandbox = await sandbox_manager.get_or_create_sandbox(session_id)
    container = _container_or_404(sandbox)
    if payload.demux:
        exit_code, output = container.exec_run(
            cmd=payload.cmd,
            demux=True,
            workdir=payload.workdir,
        )
        stdout = output[0] if output and output[0] else b""
        stderr = output[1] if output and output[1] else b""
        return {
            "exit_code": exit_code,
            "stdout_base64": base64.b64encode(stdout).decode("ascii"),
            "stderr_base64": base64.b64encode(stderr).decode("ascii"),
        }

    result = container.exec_run(
        cmd=payload.cmd,
        workdir=payload.workdir,
    )
    return {
        "exit_code": result.exit_code,
        "output_base64": base64.b64encode(result.output or b"").decode("ascii"),
    }


@app.post("/internal/runtime-control/sandbox/sessions/{session_id}/container/archive", dependencies=router_dependencies)
async def put_container_archive(session_id: str, payload: ContainerArchiveRequest) -> dict[str, str]:
    sandbox = await sandbox_manager.get_or_create_sandbox(session_id)
    container = _container_or_404(sandbox)
    archive_bytes = base64.b64decode(payload.archive_base64)
    success = container.put_archive(payload.path, io.BytesIO(archive_bytes))
    if not success:
        raise HTTPException(status_code=500, detail="Failed to upload archive")
    return {"status": "ok"}


@app.get("/internal/runtime-control/sandbox/sessions/{session_id}/container/logs", dependencies=router_dependencies)
async def get_container_logs(session_id: str) -> dict[str, str]:
    sandbox = await sandbox_manager.get_sandbox(session_id)
    if sandbox is None:
        raise HTTPException(status_code=404, detail="Sandbox not found")
    container = _container_or_404(sandbox)
    return {
        "output_base64": base64.b64encode(container.logs() or b"").decode("ascii"),
    }


@app.post("/internal/runtime-control/previews/video/deploy", dependencies=router_dependencies)
async def deploy_video_preview(payload: VideoDeployRequest) -> dict[str, Any]:
    return await video_deployer.deploy(task_id=payload.task_id, session_id=payload.session_id)


@app.post("/internal/runtime-control/previews/cleanup/session/{session_id}", dependencies=router_dependencies)
async def cleanup_session_previews(session_id: str) -> dict[str, str]:
    await preview_runtime_manager.cleanup_session_previews(session_id)
    return {"status": "ok"}


@app.post("/internal/runtime-control/previews/cleanup/all", dependencies=router_dependencies)
async def cleanup_all_previews() -> dict[str, str]:
    await preview_runtime_manager.cleanup_all_previews()
    return {"status": "ok"}


@app.post("/internal/runtime-control/previews/dashboard/deploy", dependencies=router_dependencies)
async def deploy_dashboard_preview(payload: DashboardDeployRequest) -> dict[str, Any]:
    source_archive_bytes: bytes | None = None
    if payload.source_archive_base64:
        try:
            source_archive_bytes = base64.b64decode(payload.source_archive_base64)
        except Exception as exc:
            raise HTTPException(status_code=400, detail="Invalid dashboard source archive") from exc
    if source_archive_bytes is None and not payload.local_va_app_path:
        raise HTTPException(
            status_code=422,
            detail="Either local_va_app_path or source_archive_base64 is required",
        )
    return await dashboard_deployer.deploy(
        task_id=payload.task_id,
        local_va_app_path=payload.local_va_app_path,
        source_archive_bytes=source_archive_bytes,
        session_id=payload.session_id,
    )
