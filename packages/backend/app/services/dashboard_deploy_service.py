import asyncio
import io
import os
import socket
import tarfile
from typing import Dict

import docker
from docker.errors import ImageNotFound, NotFound

from app.core.config import settings
from app.services.docker_build_paths import resolve_docker_build_target
from deepeye.utils.logger import logger


class DashboardDeployService:
    def __init__(self):
        try:
            self.docker_client = docker.from_env()
        except Exception as e:
            logger.error(f"Failed to init docker client: {e}")
            self.docker_client = None

    async def deploy(self, task_id: str, local_va_app_path: str) -> Dict:
        """
        Deploy a Dashboard to an independent container.

        Args:
            task_id: Task ID (or node_id)
            local_va_app_path: Local directory containing generated va_app source code.

        Returns:
            {
                "status": "running"|"error",
                "container_name": str,
                "url": str
            }
        """
        if not self.docker_client:
            raise RuntimeError("Docker not available")

        if not os.path.isdir(local_va_app_path):
            raise FileNotFoundError(f"Dashboard source path not found: {local_va_app_path}")

        self._ensure_dashboard_image()

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
            labels={"type": "dashboard-instance", "task_id": task_id},
            network=network_name,
        )

        try:
            self._upload_dashboard_source(container, local_va_app_path)

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

            return {
                "status": "running" if is_ready else "error",
                "container_name": container_name,
                "url": dashboard_url,
            }
        except Exception:
            logger.exception("[DashboardDeployService] Deployment failed for task_id=%s", task_id)
            raise

    def _remove_container_if_exists(self, container_name: str) -> None:
        try:
            old = self.docker_client.containers.get(container_name)
            old.remove(force=True)
            logger.info("[DashboardDeployService] Removed old container: %s", container_name)
        except NotFound:
            pass

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
        try:
            self.docker_client.images.get(settings.DASHBOARD_IMAGE)
            logger.info("[DashboardDeployService] Using image: %s", settings.DASHBOARD_IMAGE)
            return
        except ImageNotFound:
            if not settings.DASHBOARD_AUTO_BUILD:
                raise RuntimeError(
                    f"Dashboard image '{settings.DASHBOARD_IMAGE}' not found and DASHBOARD_AUTO_BUILD is disabled"
                )
        except Exception as e:
            raise RuntimeError(f"Failed to inspect dashboard image '{settings.DASHBOARD_IMAGE}': {e}")

        self._build_dashboard_image()

    def _build_dashboard_image(self) -> None:
        build_context, dockerfile_name, dockerfile_path = resolve_docker_build_target(
            dockerfile_setting=settings.DASHBOARD_DOCKERFILE,
            default_context_root=settings.SANDBOX_BUILD_CONTEXT,
            anchor_file=__file__,
        )
        if not dockerfile_path.exists():
            raise RuntimeError(f"Dashboard Dockerfile not found: {dockerfile_path}")
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
                rm=True,
            )
            logger.info("[DashboardDeployService] Built image: %s", settings.DASHBOARD_IMAGE)
        except Exception as e:
            raise RuntimeError(f"Failed to build dashboard image: {e}")

    def _upload_dashboard_source(self, container, local_va_app_path: str) -> None:
        logger.info("[DashboardDeployService] Uploading dashboard code from %s", local_va_app_path)
        tar_stream = io.BytesIO()
        with tarfile.open(fileobj=tar_stream, mode="w") as tar:
            for item in os.listdir(local_va_app_path):
                item_path = os.path.join(local_va_app_path, item)
                tar.add(item_path, arcname=item)

        tar_stream.seek(0)
        container.put_archive("/app", tar_stream)

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
