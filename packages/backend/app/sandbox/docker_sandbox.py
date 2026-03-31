"""Docker Sandbox Implementation"""

import asyncio
import os
import shlex
import time
from typing import Any

import docker
from docker.errors import DockerException, NotFound

from deepeye.sandbox import CommandResult, SandboxProtocol
from deepeye.utils.logger import logger
from app.core.config import settings


class DockerSandbox:
    """
    Docker sandbox implementation with Named Volume persistence.
    
    Uses project's Dockerfile (docker/Dockerfile.sandbox) for container initialization.
    Implements SandboxProtocol (create, destroy) with bash execution support.
    
    Data Persistence:
    - Each session gets a dedicated Docker Named Volume (deepeye-ws-{session_id})
    - Volume persists across container restarts/recreations
    - Data is only deleted when explicitly requested (destroy_with_data)
    """

    def __init__(self):
        """Initialize Docker sandbox using project config."""
        try:
            self.docker_client = docker.from_env()
        except DockerException as e:
            raise RuntimeError(f"Failed to initialize Docker client: {e}")

        self.container = None
        self.container_name: str | None = None
        self.volume_name: str | None = None
        self.session_id: str | None = None
        self._created = False

    # ============ SandboxProtocol Required Methods ============

    async def create(self, session_id: str = None) -> None:
        """
        Create and start Docker container with persistent volume (implements Protocol).
        
        Args:
            session_id: Optional session ID for container labeling (enables cross-process lookup)
        
        Volume Persistence:
        - Creates a Named Volume (deepeye-ws-{session_id}) if it doesn't exist
        - Reuses existing volume if present (data persists across container recreations)
        - Volume is mounted to /workspace in the container
        """
        if self._created:
            return

        try:
            # Ensure image exists (build if needed)
            await self._ensure_image()

            # Generate unique container name
            timestamp = int(time.time() * 1000)
            self.container_name = f"deepeye-sandbox-{timestamp}"
            self.session_id = session_id
            
            # Create or reuse Named Volume for data persistence
            self.volume_name = f"deepeye-ws-{session_id}" if session_id else f"deepeye-ws-{timestamp}"
            volume_existed = await self._ensure_volume()

            # Build labels
            labels = {
                "app": "deepeye",
                "component": "sandbox",
                "volume": self.volume_name,
            }
            if session_id:
                labels["session_id"] = session_id

            # Create and start container with volume mounted
            self.container = self.docker_client.containers.run(**self._build_container_run_kwargs(labels))
            self._created = True

            # Wait until ready
            await self._wait_until_ready()

            if volume_existed:
                logger.info(f"[DockerSandbox] Created: {self.container_name} (reused volume {self.volume_name})")
            else:
                logger.info(f"[DockerSandbox] Created: {self.container_name} (new volume {self.volume_name})")

        except DockerException as e:
            self._created = False
            raise RuntimeError(f"Failed to create sandbox: {e}")

    async def stop(self) -> None:
        """Stop container but preserve data (implements Protocol)"""
        if not self._created or not self.container:
            return

        try:
            self.container.stop(timeout=5)
            logger.info(f"[DockerSandbox] Stopped: {self.container_name} (data preserved)")
        except NotFound:
            pass
        except Exception as e:
            logger.error(f"[DockerSandbox] Error stopping container: {e}")

    async def start(self) -> None:
        """Start stopped container (implements Protocol)"""
        if not self._created or not self.container:
            raise RuntimeError("Container not created")

        try:
            self.container.start()
            await self._wait_until_ready()
            logger.info(f"[DockerSandbox] Started: {self.container_name}")
        except Exception as e:
            raise RuntimeError(f"Failed to start container: {e}")

    async def restart(self) -> None:
        """Restart container (DockerSandbox specific)"""
        await self.stop()
        await self.start()
        logger.info(f"[DockerSandbox] Restarted: {self.container_name}")

    async def destroy(self) -> None:
        """
        Stop and remove container but PRESERVE volume data (implements Protocol).
        
        The Named Volume is kept so data persists for future containers.
        Use destroy_with_data() to also delete the volume.
        """
        if not self._created:
            return

        try:
            if self.container:
                try:
                    self.container.stop(timeout=5)
                    self.container.remove(force=True)
                    logger.info(f"[DockerSandbox] Destroyed container: {self.container_name} (volume {self.volume_name} preserved)")
                except NotFound:
                    pass
                except Exception as e:
                    logger.error(f"[DockerSandbox] Error destroying container: {e}")

        except Exception as e:
            logger.error(f"[DockerSandbox] Cleanup error: {e}")
        finally:
            self._created = False
            self.container = None

    async def destroy_with_data(self) -> None:
        """
        Stop and remove container AND delete the volume (all data lost).
        
        Use this when you want to completely clean up a session.
        """
        # First destroy the container
        await self.destroy()
        
        # Then delete the volume
        if self.volume_name:
            try:
                volume = self.docker_client.volumes.get(self.volume_name)
                volume.remove(force=True)
                logger.info(f"[DockerSandbox] Deleted volume: {self.volume_name}")
            except NotFound:
                pass
            except Exception as e:
                logger.error(f"[DockerSandbox] Error deleting volume {self.volume_name}: {e}")

    # ============ DockerSandbox Specific Feature ============

    async def exec_command(self, command: str) -> CommandResult:
        """Execute bash command in sandbox"""
        if not self._created or not self.container:
            raise RuntimeError("Sandbox not created. Call create() first.")

        start_time = time.time()

        try:
            exit_code, output = self.container.exec_run(
                cmd=self._build_exec_command(command),
                demux=True,
                workdir="/workspace",
            )

            stdout = output[0].decode("utf-8") if output[0] else ""
            stderr = output[1].decode("utf-8") if output[1] else ""

            execution_time_ms = int((time.time() - start_time) * 1000)

            return CommandResult(
                stdout=stdout,
                stderr=stderr,
                exit_code=exit_code,
                execution_time_ms=execution_time_ms,
            )

        except Exception as e:
            execution_time_ms = int((time.time() - start_time) * 1000)
            return CommandResult(
                stdout="",
                stderr=f"Command execution error: {str(e)}",
                exit_code=-1,
                execution_time_ms=execution_time_ms,
            )

    async def write_file(self, path: str, data: bytes) -> None:
        """Write bytes to a file in the sandbox"""
        if not self._created or not self.container:
            raise RuntimeError("Sandbox not created")

        import tarfile
        import io

        # Create a tar archive in memory containing the file
        tar_stream = io.BytesIO()
        with tarfile.open(fileobj=tar_stream, mode='w') as tar:
            tarinfo = tarfile.TarInfo(name=os.path.basename(path))
            tarinfo.size = len(data)
            tar.addfile(tarinfo, io.BytesIO(data))
        
        tar_stream.seek(0)
        
        # Ensure directory exists
        dir_path = os.path.dirname(path)
        if dir_path and dir_path != "/":
            result = await self.exec_command(f"mkdir -p {shlex.quote(dir_path)}")
            if result.exit_code != 0:
                raise RuntimeError(result.stderr or "failed to create sandbox directory")

        # Put archive into container
        if not self.container.put_archive(dir_path or "/", tar_stream):
            raise RuntimeError(f"failed to write file to sandbox: {path}")

    async def write_text_file(self, path: str, content: str, encoding: str = "utf-8") -> None:
        """Write text content to a file in the sandbox."""
        await self.write_file(path, content.encode(encoding))

    async def health_check(self) -> bool:
        """Check if container is running"""
        return self.is_running()

    def is_running(self) -> bool:
        """Check if the underlying container is running."""
        if not self._created or not self.container:
            return False

        try:
            self.container.reload()
            return self.container.status == "running"
        except Exception:
            return False

    @property
    def is_created(self) -> bool:
        """Check if sandbox is created"""
        return self._created

    # ============ Context Manager Support ============

    async def __aenter__(self):
        await self.create()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.destroy()

    # ============ Internal Helper Methods ============

    async def _ensure_volume(self) -> bool:
        """
        Ensure Named Volume exists, create if needed.
        
        Returns:
            True if volume already existed, False if newly created
        """
        try:
            self.docker_client.volumes.get(self.volume_name)
            logger.debug(f"[DockerSandbox] Reusing existing volume: {self.volume_name}")
            return True
        except NotFound:
            # Create new volume with labels
            self.docker_client.volumes.create(
                name=self.volume_name,
                labels={
                    "app": "deepeye",
                    "component": "sandbox-data",
                    "session_id": self.session_id or ""
                }
            )
            logger.debug(f"[DockerSandbox] Created new volume: {self.volume_name}")
            return False

    async def _ensure_image(self) -> None:
        """Ensure image exists, build from project Dockerfile if needed"""
        try:
            self.docker_client.images.get(settings.SANDBOX_IMAGE)
            logger.info(f"[DockerSandbox] Using image: {settings.SANDBOX_IMAGE}")
            return
        except docker.errors.ImageNotFound:
            if not settings.SANDBOX_AUTO_BUILD:
                raise RuntimeError(
                    f"Image '{settings.SANDBOX_IMAGE}' not found. "
                    f"Build manually or set SANDBOX_AUTO_BUILD=True"
                )

            logger.info(f"[DockerSandbox] Building from {settings.SANDBOX_DOCKERFILE}...")
            await self._build_image()

    async def _build_image(self) -> None:
        """Build image from project Dockerfile"""
        try:
            image, build_logs = self.docker_client.images.build(
                path=settings.SANDBOX_BUILD_CONTEXT,
                dockerfile=settings.SANDBOX_DOCKERFILE,
                tag=settings.SANDBOX_IMAGE,
                rm=True,
                forcerm=True,
            )

            # Print build logs
            for log in build_logs:
                if 'stream' in log:
                    logger.debug(f"[DockerSandbox] {log['stream'].strip()}")
            
            logger.info(f"[DockerSandbox] Built: {settings.SANDBOX_IMAGE}")

        except DockerException as e:
            raise RuntimeError(f"Failed to build image: {e}")

    def _build_container_run_kwargs(self, labels: dict[str, str]) -> dict[str, Any]:
        tmpfs_size_bytes = max(int(settings.SANDBOX_TMPFS_SIZE_MB), 16) * 1024 * 1024
        run_kwargs: dict[str, Any] = {
            "image": settings.SANDBOX_IMAGE,
            "name": self.container_name,
            "detach": True,
            "working_dir": "/workspace",
            "command": "sleep infinity",
            "labels": labels,
            "init": settings.SANDBOX_INIT_PROCESS,
            "network_disabled": settings.SANDBOX_NETWORK_DISABLED,
            "environment": {
                "HOME": "/tmp",
                "XDG_CACHE_HOME": "/tmp/.cache",
                "MPLCONFIGDIR": "/tmp/matplotlib",
                "PIP_DISABLE_PIP_VERSION_CHECK": "1",
                "PIP_NO_CACHE_DIR": "1",
                "PYTHONDONTWRITEBYTECODE": "1",
                "PYTHONUNBUFFERED": "1",
            },
            "tmpfs": {
                "/tmp": f"rw,nosuid,nodev,size={tmpfs_size_bytes}",
                "/run": "rw,nosuid,nodev,size=16777216",
            },
            "volumes": {
                self.volume_name: {
                    "bind": "/workspace",
                    "mode": "rw",
                }
            },
        }

        security_opt: list[str] = []
        if settings.SANDBOX_NO_NEW_PRIVILEGES:
            security_opt.append("no-new-privileges:true")
        if security_opt:
            run_kwargs["security_opt"] = security_opt

        if settings.SANDBOX_DROP_ALL_CAPABILITIES:
            run_kwargs["cap_drop"] = ["ALL"]

        if settings.SANDBOX_PIDS_LIMIT > 0:
            run_kwargs["pids_limit"] = settings.SANDBOX_PIDS_LIMIT

        if settings.SANDBOX_MEMORY_LIMIT:
            run_kwargs["mem_limit"] = settings.SANDBOX_MEMORY_LIMIT

        if settings.SANDBOX_MEMORY_SWAP_LIMIT:
            run_kwargs["memswap_limit"] = settings.SANDBOX_MEMORY_SWAP_LIMIT

        if settings.SANDBOX_CPU_LIMIT and settings.SANDBOX_CPU_LIMIT > 0:
            run_kwargs["nano_cpus"] = int(settings.SANDBOX_CPU_LIMIT * 1_000_000_000)

        return run_kwargs

    def _build_exec_command(self, command: str) -> list[str]:
        timeout_seconds = int(settings.SANDBOX_EXEC_TIMEOUT_SECONDS)
        if timeout_seconds <= 0:
            return ["bash", "-c", command]

        kill_after_seconds = max(5, min(30, timeout_seconds // 10 or 5))
        return [
            "timeout",
            f"--kill-after={kill_after_seconds}s",
            f"{timeout_seconds}s",
            "bash",
            "-c",
            command,
        ]

    async def _wait_until_ready(self, max_retries: int = 30, interval: float = 0.5) -> None:
        """Wait until container is ready"""
        for i in range(max_retries):
            try:
                if await self.health_check():
                    return
                await asyncio.sleep(interval)
            except Exception:
                await asyncio.sleep(interval)

        raise RuntimeError(f"Container did not become ready in {max_retries * interval}s")
