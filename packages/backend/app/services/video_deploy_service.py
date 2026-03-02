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
import unicodedata
from pathlib import Path
from typing import Dict

import docker
from docker.errors import NotFound

from app.core.config import get_video_session_root, settings
from deepeye.utils.logger import logger


def _dataset_name_from_config(config: dict) -> str:
    title = (config.get("meta") or {}).get("title") or ""
    s = "".join(c for c in title if c.isalnum() or unicodedata.category(c).startswith("L")) or ""
    return s[:20] if s else "DataAnalysis"


def _scene_id_to_filename(scene_id: str, dataset_name: str, task_id: str) -> str:
    camel = "".join(w.capitalize() for w in scene_id.split("_"))
    need_component = scene_id in ("scene_opening", "scene_closing") or (
        "stat" in scene_id.lower() or scene_id.endswith("_statistics")
    )
    if need_component:
        return f"{dataset_name}_{camel}_{task_id}ComponentAnimated.tsx"
    return f"{dataset_name}_{camel}_{task_id}Animated.tsx"


def _build_scene_registry_ts(
    config: dict,
    task_id: str,
    existing_files: set[str],
) -> str:
    """Generate scene_registry.ts that imports each TSX scene component."""
    dataset_name = _dataset_name_from_config(config)
    lines: list[str] = [
        "import type React from 'react'",
        "",
    ]
    entries: list[str] = []

    for scene in config.get("scenes") or []:
        sid = scene.get("id")
        if not sid:
            continue
        fname = _scene_id_to_filename(sid, dataset_name, task_id)
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
                    f"/api/public/video/audio/{filename}?session_id={session_id}"
                )
    return cfg


class VideoDeployService:
    IMAGE_NAME_ENV = "VIDEO_PREVIEW_IMAGE"

    def __init__(self) -> None:
        try:
            self.docker_client = docker.from_env()
        except Exception as e:
            logger.error(f"[VideoDeployService] Failed to init Docker client: {e}")
            self.docker_client = None

    def _get_image_name(self) -> str:
        return os.environ.get(self.IMAGE_NAME_ENV, settings.VIDEO_PREVIEW_IMAGE if hasattr(settings, "VIDEO_PREVIEW_IMAGE") else "deepeye-video-preview:latest")

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

        # Remove old container if it exists
        try:
            old = self.docker_client.containers.get(container_name)
            old.remove(force=True)
            logger.info(f"[VideoDeployService] Removed old container: {container_name}")
        except NotFound:
            pass

        image = self._get_image_name()
        logger.info(f"[VideoDeployService] Starting container {container_name} from {image}")

        video_url_prefix = f"/video-previews/{container_name}/"
        container = self.docker_client.containers.run(
            image=image,
            name=container_name,
            detach=True,
            labels={"type": "video-preview", "task_id": task_id, "session_id": session_id},
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
            logger.info(f"[VideoDeployService] Upload complete")

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

            return {
                "status": "running" if is_ready else "error",
                "container_name": container_name,
                "url": video_url,
            }

        except Exception as e:
            logger.error(f"[VideoDeployService] Deploy failed for task {task_id}: {e}")
            raise

    async def start_test_preview(self) -> Dict:
        """
        启动一个「测试用」预览容器（不跑真实视频生成、不花钱），用于验证：
        前端 → nginx → 预览容器 整条链路是否打通。
        使用固定 task_id 20260302_999999，容器内为最小 config + 空场景。
        """
        if not self.docker_client:
            raise RuntimeError("[VideoDeployService] Docker not available")
        task_id = "20260302_999999"
        container_name = f"deepeye-video-{task_id}"
        network_name = self._detect_network()
        try:
            old = self.docker_client.containers.get(container_name)
            old.remove(force=True)
            logger.info(f"[VideoDeployService] Removed old test container: {container_name}")
        except NotFound:
            pass
        image = self._get_image_name()
        video_url_prefix = f"/video-previews/{container_name}/"
        logger.info(f"[VideoDeployService] Starting TEST preview container {container_name} from {image}")
        container = self.docker_client.containers.run(
            image=image,
            name=container_name,
            detach=True,
            labels={"type": "video-preview", "task_id": task_id, "test": "true"},
            network=network_name,
            environment={"VITE_BASE_PATH": video_url_prefix},
        )
        try:
            minimal_config = {
                "meta": {"title": "Test Preview (no cost)", "fps": 30, "width": 1920, "height": 1080, "video_duration": 10},
                "scenes": [],
            }
            scene_registry_ts = (
                "import type React from 'react'\n"
                "export const sceneComponents: Record<string, React.FC<any>> = {}\n"
            )
            config_bytes = json.dumps(minimal_config, ensure_ascii=False, indent=2).encode("utf-8")
            registry_bytes = scene_registry_ts.encode("utf-8")
            tar_stream = io.BytesIO()
            with tarfile.open(fileobj=tar_stream, mode="w") as tar:
                def _add(name: str, data: bytes) -> None:
                    info = tarfile.TarInfo(name=name)
                    info.size = len(data)
                    tar.addfile(info, io.BytesIO(data))
                _add("config.json", config_bytes)
                _add("scene_registry.ts", registry_bytes)
                _add(".ready", b"1")
            tar_stream.seek(0)
            container.put_archive("/app/src", tar_stream)
            video_url = video_url_prefix
            for i in range(90):
                container.reload()
                if container.status != "running":
                    logs = container.logs().decode("utf-8", errors="replace")
                    logger.error(f"[VideoDeployService] Test container stopped. Logs:\n{logs}")
                    return {"status": "error", "task_id": task_id, "url": video_url}
                check = container.exec_run(
                    "node -e \"require('net').createConnection(5173,'127.0.0.1').on('connect',()=>process.exit(0)).on('error',()=>process.exit(1))\""
                )
                if check.exit_code == 0:
                    logger.info(f"[VideoDeployService] Test preview ready: {video_url}")
                    return {"status": "running", "task_id": task_id, "url": video_url}
                if i % 10 == 0 and i > 0:
                    logger.info(f"[VideoDeployService] Test container still starting... ({i}s/90s)")
                await asyncio.sleep(1)
            logger.warning("[VideoDeployService] Test preview timed out")
            return {"status": "error", "task_id": task_id, "url": video_url}
        except Exception as e:
            logger.error(f"[VideoDeployService] Test preview failed: {e}")
            raise


# Singleton
video_deployer = VideoDeployService()
