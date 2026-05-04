"""
VideoDeployService - deploys each generated data video to an independent container
for production-safe iframe preview (no browser-side TSX compilation needed).

Architecture:
  VideoGeneratorHandler produces:
    - /workspace/sessions/{session_id}/video_configs/generated_{task_id}_aligned.json
    - /workspace/sessions/{session_id}/video_components/{task_id}/*.tsx

  This service:
    1. Reads those files from the host workspace volume.
    2. Generates scene_registry.ts (maps scene_id → TSX component export).
    3. Rewrites audio_file paths to full API URLs accessible by the browser.
    4. Spins up a container from the VIDEO_PREVIEW_IMAGE.
    5. Uploads config.json + TSX files + scene_registry.ts into /app/src/.
    6. Creates /app/src/.ready so start.sh launches Vite.
    7. Waits for port 5173 to accept connections.
    8. Returns the proxy URL  /video-previews/deepeye-video-{task_id}/.
"""

from __future__ import annotations

import asyncio
import io
import json
import os
import re
import tarfile
import time
from pathlib import Path
from typing import Dict

import docker
from docker.errors import ImageNotFound, NotFound

from app.core.config import get_video_session_root, settings
from app.deploy.services.video_naming import expected_scene_component_files
from app.infra.services.docker_build_paths import resolve_docker_build_target
from app.infra.services.docker_control import get_docker_control_client
from app.runtime.services.metrics import runtime_metrics
from app.runtime.services.preview import preview_container_labels, preview_containers_to_cleanup
from deepeye.utils.logger import logger


def _build_scene_registry_ts(
    config: dict,
    task_id: str,
    existing_files: set[str],
) -> str:
    """Generate scene_registry.ts that imports each TSX scene component."""
    lines: list[str] = [
        "import type React from 'react'",
        "",
    ]
    entries: list[str] = []

    for sid, fname in expected_scene_component_files(config, task_id).items():
        if fname not in existing_files:
            continue
        # Safe import alias (replace non-alnum with _)
        alias = "mod_" + re.sub(r"[^a-zA-Z0-9]", "_", sid)
        stem = fname[: -len(".tsx")]  # remove .tsx for import path
        lines.append(f"import * as {alias} from './{stem}'")
        entries.append(
            f"  '{sid}': (({alias} as any).default"
            f" || Object.values({alias} as any).find((v: any) => typeof v === 'function')) as React.FC<any>,"
        )

    lines += [
        "",
        "export const sceneComponents: Record<string, React.FC<any>> = {",
        *entries,
        "}",
        "",
    ]
    return "\n".join(lines)


def _rewrite_audio_urls(config: dict, session_id: str) -> dict:
    """Rewrite relative audio_file values to full backend API URLs."""
    import copy
    cfg = copy.deepcopy(config)
    for scene in cfg.get("scenes") or []:
        for narr in scene.get("narration") or []:
            af = narr.get("audio_file")
            if af and not af.startswith("http") and not af.startswith("/api"):
                filename = Path(af).name
                narr["audio_file"] = (
                    f"/api/v1/video/audio/{filename}?session_id={session_id}"
                )
    return cfg


class VideoDeployService:
    IMAGE_NAME_ENV = "VIDEO_PREVIEW_IMAGE"

    def __init__(self) -> None:
        self._control_client = get_docker_control_client()
        if settings.DOCKER_CONTROL_MODE == "remote":
            self.docker_client = None
            return
        try:
            self.docker_client = docker.from_env()
        except Exception as e:
            logger.error(f"[VideoDeployService] Failed to init Docker client: {e}")
            self.docker_client = None

    def _get_image_name(self) -> str:
        return os.environ.get(self.IMAGE_NAME_ENV, settings.VIDEO_PREVIEW_IMAGE)

    def _cleanup_preview_containers(self) -> None:
        containers = self.docker_client.containers.list(
            all=True,
            filters={"label": ["preview_kind=video"]},
        )
        for container in preview_containers_to_cleanup(
            containers,
            ttl_seconds=settings.PREVIEW_RUNTIME_TTL_SECONDS,
            max_running=settings.PREVIEW_RUNTIME_MAX_CONTAINERS,
        ):
            try:
                container.remove(force=True)
                logger.info("[VideoDeployService] Removed stale preview container: %s", container.name)
            except Exception as exc:
                logger.warning("[VideoDeployService] Failed to remove preview container %s: %s", container.name, exc)

    def _ensure_preview_image(self, image_name: str) -> None:
        try:
            self.docker_client.images.get(image_name)
            logger.info("[VideoDeployService] Using image: %s", image_name)
            return
        except ImageNotFound:
            if not settings.VIDEO_PREVIEW_AUTO_BUILD:
                raise RuntimeError(
                    f"Video preview image '{image_name}' not found and VIDEO_PREVIEW_AUTO_BUILD is disabled"
                )
        except Exception as e:
            raise RuntimeError(f"Failed to inspect video preview image '{image_name}': {e}")

        self._build_preview_image(image_name)

    def _build_preview_image(self, image_name: str) -> None:
        build_context, dockerfile_name, dockerfile_path = resolve_docker_build_target(
            dockerfile_setting=settings.VIDEO_PREVIEW_DOCKERFILE,
            default_context_root=settings.SANDBOX_BUILD_CONTEXT,
            anchor_file=__file__,
        )
        if not dockerfile_path.exists():
            raise RuntimeError(f"Video preview Dockerfile not found: {dockerfile_path}")
        logger.info(
            "[VideoDeployService] Building image %s from %s (context=%s)",
            image_name,
            dockerfile_path,
            build_context,
        )
        try:
            self.docker_client.images.build(
                path=build_context,
                dockerfile=dockerfile_name,
                tag=image_name,
                rm=True,
            )
            logger.info("[VideoDeployService] Built image: %s", image_name)
        except Exception as e:
            raise RuntimeError(f"Failed to build video preview image '{image_name}': {e}")

    def _detect_network(self) -> str:
        default = "deepeye_default"
        try:
            import socket
            hostname = socket.gethostname()
            this = self.docker_client.containers.get(hostname)
            networks = this.attrs["NetworkSettings"]["Networks"]
            biz = [n for n in networks if n != "bridge"]
            return biz[0] if biz else list(networks.keys())[0]
        except Exception as e:
            logger.warning(f"[VideoDeployService] Network detection failed: {e}, using {default}")
            return default

    async def deploy(
        self,
        task_id: str,
        session_id: str,
    ) -> Dict:
        """
        Deploy video preview container for a completed video generation task.

        Args:
            task_id:    Task ID in YYYYMMDD_HHMMSS format.
            session_id: Session ID used to locate workspace files.

        Returns:
            {"status": "running"|"error", "container_name": str, "url": str}
        """
        start_time = time.perf_counter()
        if settings.DOCKER_CONTROL_MODE == "remote":
            try:
                result = await self._control_client.deploy_video_preview(
                    task_id=task_id,
                    session_id=session_id,
                )
                runtime_metrics.increment(
                    "preview.deploy.count",
                    tags={"kind": "video", "mode": "remote", "status": "success"},
                )
                runtime_metrics.record_duration(
                    "preview.deploy.duration_seconds",
                    time.perf_counter() - start_time,
                    tags={"kind": "video", "mode": "remote"},
                )
                return result
            except Exception:
                runtime_metrics.increment(
                    "preview.deploy.count",
                    tags={"kind": "video", "mode": "remote", "status": "failed"},
                )
                raise

        if not self.docker_client:
            raise RuntimeError("[VideoDeployService] Docker not available")

        session_root = get_video_session_root(session_id)
        config_path = session_root / "video_configs" / f"generated_{task_id}_aligned.json"
        components_dir = session_root / "video_components" / task_id

        if not config_path.exists():
            raise FileNotFoundError(f"Config not found: {config_path}")
        if not components_dir.exists():
            raise FileNotFoundError(f"Components dir not found: {components_dir}")

        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)

        tsx_files = {p.name for p in components_dir.glob("*.tsx")}
        if not tsx_files:
            raise FileNotFoundError(f"No TSX files in {components_dir}")

        container_name = f"deepeye-video-{task_id}"
        network_name = self._detect_network()

        image = self._get_image_name()
        self._ensure_preview_image(image)
        self._cleanup_preview_containers()

        # Remove old container if it exists
        try:
            old = self.docker_client.containers.get(container_name)
            old.remove(force=True)
            logger.info(f"[VideoDeployService] Removed old container: {container_name}")
        except NotFound:
            pass

        logger.info(f"[VideoDeployService] Starting container {container_name} from {image}")

        video_url_prefix = f"/video-previews/{container_name}/"
        container = self.docker_client.containers.run(
            image=image,
            name=container_name,
            detach=True,
            labels={
                **preview_container_labels(preview_kind="video", task_id=task_id, session_id=session_id),
                "type": "video-preview",
            },
            network=network_name,
            environment={"VITE_BASE_PATH": video_url_prefix},
        )

        try:
            # Build tar archive: config.json + all TSX files + scene_registry.ts + .ready sentinel
            scene_registry_ts = _build_scene_registry_ts(config, task_id, tsx_files)
            rewritten_config = _rewrite_audio_urls(config, session_id)
            config_bytes = json.dumps(rewritten_config, ensure_ascii=False, indent=2).encode("utf-8")
            registry_bytes = scene_registry_ts.encode("utf-8")

            tar_stream = io.BytesIO()
            with tarfile.open(fileobj=tar_stream, mode="w") as tar:
                def _add_bytes(name: str, data: bytes) -> None:
                    info = tarfile.TarInfo(name=name)
                    info.size = len(data)
                    tar.addfile(info, io.BytesIO(data))

                _add_bytes("config.json", config_bytes)
                _add_bytes("scene_registry.ts", registry_bytes)

                for tsx_name in tsx_files:
                    tsx_path = components_dir / tsx_name
                    with open(tsx_path, "rb") as f:
                        tsx_data = f.read()
                    _add_bytes(tsx_name, tsx_data)

                # sentinel: triggers start.sh to launch Vite
                _add_bytes(".ready", b"1")

            tar_stream.seek(0)

            logger.info(f"[VideoDeployService] Uploading {len(tsx_files)} TSX files + config to {container_name}")
            container.put_archive("/app/src", tar_stream)
            logger.info("[VideoDeployService] Upload complete")

            # Wait for Vite port 5173
            video_url = video_url_prefix
            logger.info(f"[VideoDeployService] Waiting for Vite to be ready at {video_url} ...")

            is_ready = False
            for i in range(90):
                container.reload()
                if container.status != "running":
                    logs = container.logs().decode("utf-8", errors="replace")
                    logger.error(f"[VideoDeployService] Container stopped. Logs:\n{logs}")
                    break

                check = container.exec_run(
                    "node -e \"require('net').createConnection(5173,'127.0.0.1').on('connect',()=>process.exit(0)).on('error',()=>process.exit(1))\""
                )
                if check.exit_code == 0:
                    logger.info(f"[VideoDeployService] Vite ready: {video_url}")
                    is_ready = True
                    break

                if i % 10 == 0 and i > 0:
                    logger.info(f"[VideoDeployService] Still waiting... ({i}s/90s)")

                await asyncio.sleep(1)

            if not is_ready:
                logs = container.logs().decode("utf-8", errors="replace")
                logger.error(f"[VideoDeployService] Deployment timed out.\n{logs[-2000:]}")

            runtime_metrics.increment(
                "preview.deploy.count",
                tags={"kind": "video", "mode": "local", "status": "success" if is_ready else "failed"},
            )
            return {
                "status": "running" if is_ready else "error",
                "container_name": container_name,
                "url": video_url,
            }

        except Exception as e:
            logger.error(f"[VideoDeployService] Deploy failed for task {task_id}: {e}")
            runtime_metrics.increment(
                "preview.deploy.count",
                tags={"kind": "video", "mode": "local", "status": "failed"},
            )
            raise
        finally:
            runtime_metrics.record_duration(
                "preview.deploy.duration_seconds",
                time.perf_counter() - start_time,
                tags={"kind": "video", "mode": "local"},
            )

# Singleton
video_deployer = VideoDeployService()
