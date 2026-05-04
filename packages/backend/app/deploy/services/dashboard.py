import asyncio
import hashlib
import io
import json
import os
import socket
import tarfile
import time
from pathlib import Path
from typing import Dict

import docker
from docker.errors import ImageNotFound, NotFound

from app.core.config import settings
from app.infra.services.docker_build_paths import resolve_docker_build_target
from app.infra.services.docker_control import get_docker_control_client
from app.runtime.services.metrics import runtime_metrics
from app.runtime.services.preview import preview_container_labels, preview_containers_to_cleanup
from deepeye.utils.logger import logger


_DASHBOARD_CORS_FALLBACK_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]
_DASHBOARD_IMAGE_SOURCE_HASH_LABEL = "deepeye.dashboard.dockerfile_sha256"


def _resolve_dashboard_cors_origins() -> list[str]:
    origins = [str(origin).rstrip("/") for origin in settings.BACKEND_CORS_ORIGINS]
    origins = [origin for origin in origins if origin and origin != "*"]
    if origins:
        return origins
    logger.warning(
        "[DashboardDeployService] BACKEND_CORS_ORIGINS contains wildcard or is empty. "
        "Falling back to localhost origins for dashboard previews."
    )
    return list(_DASHBOARD_CORS_FALLBACK_ORIGINS)


def _dashboard_container_environment() -> dict[str, str]:
    return {
        "BACKEND_CORS_ORIGINS": json.dumps(_resolve_dashboard_cors_origins()),
    }


def _compute_file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _resolve_dashboard_build_target() -> tuple[str, str, Path]:
    build_context, dockerfile_name, dockerfile_path = resolve_docker_build_target(
        dockerfile_setting=settings.DASHBOARD_DOCKERFILE,
        default_context_root=settings.SANDBOX_BUILD_CONTEXT,
        anchor_file=__file__,
    )
    if not dockerfile_path.exists():
        raise RuntimeError(f"Dashboard Dockerfile not found: {dockerfile_path}")
    return build_context, dockerfile_name, dockerfile_path


def _dashboard_image_source_hash(image) -> str | None:
    attrs = getattr(image, "attrs", {}) or {}
    config = attrs.get("Config", {}) or {}
    labels = config.get("Labels", {}) or {}
    return labels.get(_DASHBOARD_IMAGE_SOURCE_HASH_LABEL)


class DashboardDeployService:
    def __init__(self):
        self._control_client = get_docker_control_client()
        if settings.DOCKER_CONTROL_MODE == "remote":
            self.docker_client = None
            return
        try:
            self.docker_client = docker.from_env()
        except Exception as e:
            logger.error(f"Failed to init docker client: {e}")
            self.docker_client = None

    async def deploy(
        self,
        task_id: str,
        local_va_app_path: str | None = None,
        source_archive_bytes: bytes | None = None,
        session_id: str | None = None,
    ) -> Dict:
        """
        Deploy a Dashboard to an independent container.

        Args:
            task_id: Task ID (or node_id)
            local_va_app_path: Local directory containing generated va_app source code.
            source_archive_bytes: Tar archive containing dashboard source files at the archive root.

        Returns:
            {
                "status": "running"|"error",
                "container_name": str,
                "url": str
            }
        """
        start_time = time.perf_counter()
        if source_archive_bytes is None:
            if not local_va_app_path:
                raise ValueError("Either local_va_app_path or source_archive_bytes is required")
            source_archive_bytes = self._build_dashboard_source_archive(local_va_app_path)

        if settings.DOCKER_CONTROL_MODE == "remote":
            try:
                result = await self._control_client.deploy_dashboard_preview(
                    task_id=task_id,
                    source_archive_bytes=source_archive_bytes,
                    session_id=session_id,
                )
                runtime_metrics.increment(
                    "preview.deploy.count",
                    tags={"kind": "dashboard", "mode": "remote", "status": "success"},
                )
                runtime_metrics.record_duration(
                    "preview.deploy.duration_seconds",
                    time.perf_counter() - start_time,
                    tags={"kind": "dashboard", "mode": "remote"},
                )
                return result
            except Exception:
                runtime_metrics.increment(
                    "preview.deploy.count",
                    tags={"kind": "dashboard", "mode": "remote", "status": "failed"},
                )
                raise

        if not self.docker_client:
            raise RuntimeError("Docker not available")

        self._ensure_dashboard_image()
        self._cleanup_preview_containers()

        container_name = f"deepeye-nl2dashboard-{task_id}"
        network_name = self._detect_network_name()

        self._remove_container_if_exists(container_name)

        start_cmd = (
            "bash -lc '"
            "echo [SYSTEM] Waiting for dashboard code upload...; "
            "while [ ! -f /app/app.py ]; do sleep 0.2; done; "
            "echo [SYSTEM] Starting Dashboard Uvicorn...; "
            "cd /app && "
            "export PYTHONPATH=/app:$PYTHONPATH && "
            "exec python3 -m uvicorn app:app --host 0.0.0.0 --port 8000"
            "'"
        )

        logger.info(
            "[DashboardDeployService] Starting container %s from %s on network %s",
            container_name,
            settings.DASHBOARD_IMAGE,
            network_name,
        )

        container = self.docker_client.containers.run(
            image=settings.DASHBOARD_IMAGE,
            name=container_name,
            detach=True,
            working_dir="/app",
            command=start_cmd,
            environment=_dashboard_container_environment(),
            labels={
                **preview_container_labels(
                    preview_kind="dashboard",
                    task_id=task_id,
                    session_id=session_id,
                ),
                "type": "dashboard-instance",
            },
            network=network_name,
        )

        try:
            self._upload_dashboard_source_archive(container, source_archive_bytes)

            await asyncio.sleep(1)
            container.reload()
            if container.status != "running":
                logs = container.logs().decode("utf-8", errors="replace")
                raise RuntimeError(
                    f"Container stopped after upload: {container.status}\n{logs}"
                )

            dashboard_url = f"/dashboards/{container_name}/"
            is_ready = await self._wait_for_port_ready(container, timeout_seconds=60)
            if not is_ready:
                logs = container.logs().decode("utf-8", errors="replace")
                logger.error("[DashboardDeployService] Deployment timeout. Logs:\n%s", logs)

            runtime_metrics.increment(
                "preview.deploy.count",
                tags={"kind": "dashboard", "mode": "local", "status": "success" if is_ready else "failed"},
            )
            return {
                "status": "running" if is_ready else "error",
                "container_name": container_name,
                "url": dashboard_url,
            }
        except Exception:
            logger.exception("[DashboardDeployService] Deployment failed for task_id=%s", task_id)
            runtime_metrics.increment(
                "preview.deploy.count",
                tags={"kind": "dashboard", "mode": "local", "status": "failed"},
            )
            raise
        finally:
            runtime_metrics.record_duration(
                "preview.deploy.duration_seconds",
                time.perf_counter() - start_time,
                tags={"kind": "dashboard", "mode": "local"},
            )

    def _remove_container_if_exists(self, container_name: str) -> None:
        try:
            old = self.docker_client.containers.get(container_name)
            old.remove(force=True)
            logger.info("[DashboardDeployService] Removed old container: %s", container_name)
        except NotFound:
            pass

    def _cleanup_preview_containers(self) -> None:
        containers = self.docker_client.containers.list(
            all=True,
            filters={"label": ["preview_kind=dashboard"]},
        )
        for container in preview_containers_to_cleanup(
            containers,
            ttl_seconds=settings.PREVIEW_RUNTIME_TTL_SECONDS,
            max_running=settings.PREVIEW_RUNTIME_MAX_CONTAINERS,
        ):
            try:
                container.remove(force=True)
                logger.info("[DashboardDeployService] Removed stale preview container: %s", container.name)
            except Exception as exc:
                logger.warning(
                    "[DashboardDeployService] Failed to remove preview container %s: %s",
                    container.name,
                    exc,
                )

    def _detect_network_name(self) -> str:
        """Try to keep dashboard containers on the same network as current backend container."""
        fallback_network = "bridge"
        try:
            hostname = socket.gethostname()
            this_container = self.docker_client.containers.get(hostname)
            networks = this_container.attrs.get("NetworkSettings", {}).get("Networks", {})
            biz_networks = [name for name in networks.keys() if name != "bridge"]
            if biz_networks:
                return biz_networks[0]
            if networks:
                return next(iter(networks.keys()))
        except Exception as e:
            logger.warning("[DashboardDeployService] Auto network detection failed: %s", e)

        return fallback_network

    def _ensure_dashboard_image(self) -> None:
        build_context, dockerfile_name, dockerfile_path = _resolve_dashboard_build_target()
        expected_source_hash = _compute_file_sha256(dockerfile_path)
        try:
            image = self.docker_client.images.get(settings.DASHBOARD_IMAGE)
            current_source_hash = _dashboard_image_source_hash(image)
            if current_source_hash == expected_source_hash:
                logger.info("[DashboardDeployService] Using image: %s", settings.DASHBOARD_IMAGE)
                return
            if not settings.DASHBOARD_AUTO_BUILD:
                raise RuntimeError(
                    f"Dashboard image '{settings.DASHBOARD_IMAGE}' is outdated and DASHBOARD_AUTO_BUILD is disabled"
                )
            logger.info(
                "[DashboardDeployService] Rebuilding image %s due to Dockerfile change (current=%s expected=%s)",
                settings.DASHBOARD_IMAGE,
                current_source_hash or "missing",
                expected_source_hash,
            )
        except ImageNotFound:
            if not settings.DASHBOARD_AUTO_BUILD:
                raise RuntimeError(
                    f"Dashboard image '{settings.DASHBOARD_IMAGE}' not found and DASHBOARD_AUTO_BUILD is disabled"
                )
        except Exception as e:
            raise RuntimeError(f"Failed to inspect dashboard image '{settings.DASHBOARD_IMAGE}': {e}")

        self._build_dashboard_image(
            build_context=build_context,
            dockerfile_name=dockerfile_name,
            dockerfile_path=dockerfile_path,
            expected_source_hash=expected_source_hash,
        )

    def _build_dashboard_image(
        self,
        *,
        build_context: str,
        dockerfile_name: str,
        dockerfile_path: Path,
        expected_source_hash: str,
    ) -> None:
        logger.info(
            "[DashboardDeployService] Building image %s from %s (context=%s)",
            settings.DASHBOARD_IMAGE,
            dockerfile_path,
            build_context,
        )
        try:
            self.docker_client.images.build(
                path=build_context,
                dockerfile=dockerfile_name,
                tag=settings.DASHBOARD_IMAGE,
                labels={_DASHBOARD_IMAGE_SOURCE_HASH_LABEL: expected_source_hash},
                rm=True,
            )
            logger.info("[DashboardDeployService] Built image: %s", settings.DASHBOARD_IMAGE)
        except Exception as e:
            raise RuntimeError(f"Failed to build dashboard image: {e}")

    def _build_dashboard_source_archive(self, local_va_app_path: str) -> bytes:
        if not os.path.isdir(local_va_app_path):
            raise FileNotFoundError(f"Dashboard source path not found: {local_va_app_path}")
        logger.info("[DashboardDeployService] Packaging dashboard code from %s", local_va_app_path)
        tar_stream = io.BytesIO()
        with tarfile.open(fileobj=tar_stream, mode="w") as tar:
            for item in os.listdir(local_va_app_path):
                item_path = os.path.join(local_va_app_path, item)
                tar.add(item_path, arcname=item)
        return tar_stream.getvalue()

    def _upload_dashboard_source_archive(self, container, archive_bytes: bytes) -> None:
        logger.info(
            "[DashboardDeployService] Uploading dashboard code archive (%s bytes)",
            len(archive_bytes),
        )
        container.put_archive("/app", io.BytesIO(archive_bytes))

    async def _wait_for_port_ready(self, container, timeout_seconds: int) -> bool:
        for elapsed in range(timeout_seconds):
            container.reload()
            if container.status != "running":
                logger.error(
                    "[DashboardDeployService] Container exited while waiting, status=%s",
                    container.status,
                )
                return False

            check_cmd = (
                "python3 -c 'import socket; s = socket.socket(); "
                "s.settimeout(0.5); s.connect((\"127.0.0.1\", 8000))'"
            )
            res = container.exec_run(check_cmd)
            if res.exit_code == 0:
                return True

            if elapsed > 0 and elapsed % 5 == 0:
                logger.info("[DashboardDeployService] Still starting... (%ss/%ss)", elapsed, timeout_seconds)

            await asyncio.sleep(1)

        return False


# Singleton
dashboard_deployer = DashboardDeployService()
