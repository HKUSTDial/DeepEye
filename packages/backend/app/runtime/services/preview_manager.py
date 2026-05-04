from __future__ import annotations

import asyncio

import docker

from app.core.config import settings
from app.runtime.services.preview import preview_containers_to_cleanup
from app.infra.services.docker_control import get_docker_control_client
from deepeye.utils.logger import logger


_PREVIEW_KINDS = ("video", "dashboard")


class PreviewRuntimeManager:
    def __init__(self) -> None:
        self._control_client = get_docker_control_client()
        self._cleanup_task: asyncio.Task[None] | None = None
        self._running = False

        if self._use_remote_control():
            self.docker_client = None
            return

        try:
            self.docker_client = docker.from_env()
        except Exception as exc:
            logger.error("[PreviewRuntimeManager] Failed to init Docker client: %s", exc)
            self.docker_client = None

    def _use_remote_control(self) -> bool:
        return settings.DOCKER_CONTROL_MODE == "remote"

    def _list_preview_containers(
        self,
        *,
        preview_kind: str | None = None,
        session_id: str | None = None,
    ) -> list:
        if not self.docker_client:
            return []

        labels = ["component=preview-runtime"]
        if preview_kind:
            labels.append(f"preview_kind={preview_kind}")
        if session_id:
            labels.append(f"session_id={session_id}")

        return self.docker_client.containers.list(
            all=True,
            filters={"label": labels},
        )

    def _remove_container(self, container, *, reason: str) -> None:
        try:
            container.remove(force=True)
            logger.info(
                "[PreviewRuntimeManager] Removed preview container %s (%s)",
                getattr(container, "name", "<unknown>"),
                reason,
            )
        except Exception as exc:
            logger.warning(
                "[PreviewRuntimeManager] Failed to remove preview container %s: %s",
                getattr(container, "name", "<unknown>"),
                exc,
            )

    async def cleanup_session_previews(self, session_id: str) -> None:
        if self._use_remote_control():
            await self._control_client.cleanup_session_previews(session_id)
            return

        for container in self._list_preview_containers(session_id=session_id):
            self._remove_container(container, reason=f"session cleanup {session_id}")

    async def cleanup_all_previews(self) -> None:
        if self._use_remote_control():
            await self._control_client.cleanup_all_previews()
            return

        for container in self._list_preview_containers():
            self._remove_container(container, reason="cleanup all")

    async def _run_cleanup_cycle(self) -> None:
        if not self.docker_client:
            return

        for preview_kind in _PREVIEW_KINDS:
            containers = self._list_preview_containers(preview_kind=preview_kind)
            stale = preview_containers_to_cleanup(
                containers,
                ttl_seconds=settings.PREVIEW_RUNTIME_TTL_SECONDS,
                max_running=settings.PREVIEW_RUNTIME_MAX_CONTAINERS,
            )
            for container in stale:
                self._remove_container(container, reason=f"{preview_kind} janitor")

    async def _cleanup_loop(self) -> None:
        logger.info("[PreviewRuntimeManager] Starting preview cleanup task")
        while self._running:
            try:
                await self._run_cleanup_cycle()
                await asyncio.sleep(settings.PREVIEW_RUNTIME_CLEANUP_INTERVAL_SECONDS)
            except Exception as exc:
                logger.error("[PreviewRuntimeManager] Cleanup error: %s", exc)
        logger.info("[PreviewRuntimeManager] Preview cleanup task stopped")

    def start_cleanup_task(self) -> None:
        if self._use_remote_control():
            self._running = True
            return
        if self._running or not self.docker_client:
            return
        self._running = True
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())

    async def stop_cleanup_task(self) -> None:
        self._running = False
        if self._use_remote_control():
            return
        if self._cleanup_task:
            await self._cleanup_task
            self._cleanup_task = None


preview_runtime_manager = PreviewRuntimeManager()
