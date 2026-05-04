"""Docker Sandbox Implementation."""

from __future__ import annotations

import asyncio
import base64
import io
import os
import shlex
import tarfile
import time
from typing import Any

import docker
from docker.errors import DockerException, NotFound

from app.core.config import settings
from app.infra.services.docker_build_paths import resolve_docker_build_target
from app.infra.services.docker_control import get_docker_control_client
from app.runtime.services.metrics import runtime_metrics
from deepeye.sandbox import CommandResult
from deepeye.utils.logger import logger


class RemoteExecRunResult:
    def __init__(self, exit_code: int, output: bytes | tuple[bytes, bytes]) -> None:
        self.exit_code = exit_code
        self.output = output

    def __iter__(self):
        yield self.exit_code
        yield self.output


class RemoteContainerProxy:
    def __init__(self, sandbox: "DockerSandbox") -> None:
        self._sandbox = sandbox
        self.name: str | None = sandbox.container_name
        self.status: str | None = None
        self.labels: dict[str, str] = {}
        self.attrs: dict[str, Any] = {}

    def _refresh(self, payload: dict[str, Any]) -> None:
        self.name = payload.get("name")
        self.status = payload.get("status")
        labels = payload.get("labels")
        attrs = payload.get("attrs")
        self.labels = labels if isinstance(labels, dict) else {}
        self.attrs = attrs if isinstance(attrs, dict) else {}

    def reload(self) -> None:
        if not self._sandbox.session_id:
            return
        payload = self._sandbox._control_client.container_state(self._sandbox.session_id)
        self._refresh(payload)
        self._sandbox.container_name = self.name

    def exec_run(
        self,
        cmd: list[str] | str,
        demux: bool = False,
        workdir: str | None = None,
    ) -> RemoteExecRunResult:
        if not self._sandbox.session_id:
            raise RuntimeError("Sandbox session_id is not set")
        payload = self._sandbox._control_client.container_exec(
            self._sandbox.session_id,
            cmd=cmd,
            demux=demux,
            workdir=workdir,
        )
        exit_code = int(payload.get("exit_code", -1))
        if demux:
            stdout = payload.get("stdout_base64") or ""
            stderr = payload.get("stderr_base64") or ""
            return RemoteExecRunResult(
                exit_code,
                (
                    base64.b64decode(stdout),
                    base64.b64decode(stderr),
                ),
            )
        output = payload.get("output_base64") or ""
        return RemoteExecRunResult(
            exit_code,
            base64.b64decode(output),
        )

    def put_archive(self, path: str, data) -> bool:
        if not self._sandbox.session_id:
            raise RuntimeError("Sandbox session_id is not set")
        if hasattr(data, "read"):
            archive_bytes = data.read()
        else:
            archive_bytes = bytes(data)
        self._sandbox._control_client.container_put_archive(self._sandbox.session_id, path, archive_bytes)
        return True

    def start(self) -> None:
        if not self._sandbox.session_id:
            raise RuntimeError("Sandbox session_id is not set")
        self._sandbox._control_client._request(
            "POST",
            f"/internal/runtime-control/sandbox/sessions/{self._sandbox.session_id}/start",
        )
        self.reload()

    def stop(self, timeout: int = 5) -> None:
        del timeout
        if not self._sandbox.session_id:
            raise RuntimeError("Sandbox session_id is not set")
        self._sandbox._control_client._request(
            "POST",
            f"/internal/runtime-control/sandbox/sessions/{self._sandbox.session_id}/stop",
        )
        self.reload()

    def remove(self, force: bool = False) -> None:
        del force
        if not self._sandbox.session_id:
            raise RuntimeError("Sandbox session_id is not set")
        self._sandbox._control_client._request(
            "DELETE",
            f"/internal/runtime-control/sandbox/sessions/{self._sandbox.session_id}",
            params={"delete_data": "false"},
        )
        self._sandbox._created = False
        self.status = "removed"

    def logs(self) -> bytes:
        if not self._sandbox.session_id:
            raise RuntimeError("Sandbox session_id is not set")
        return self._sandbox._control_client.container_logs(self._sandbox.session_id)


class DockerSandbox:
    """
    Docker sandbox implementation with Named Volume persistence.

    In local mode it talks to Docker directly. In remote mode it proxies all
    container lifecycle and exec operations through the internal runtime-control
    service so business processes no longer need direct Docker access.
    """

    def __init__(self):
        self._control_client = get_docker_control_client()
        self.docker_client = None
        if not self._use_remote_control():
            try:
                self.docker_client = docker.from_env()
            except DockerException as e:
                raise RuntimeError(f"Failed to initialize Docker client: {e}")

        self.container = None
        self.container_name: str | None = None
        self.volume_name: str | None = None
        self.session_id: str | None = None
        self._created = False

    def _use_remote_control(self) -> bool:
        return settings.DOCKER_CONTROL_MODE == "remote"

    def _apply_remote_state(self, payload: dict[str, Any]) -> None:
        self.session_id = payload.get("session_id")
        self.container_name = payload.get("container_name")
        self.volume_name = payload.get("volume_name")
        self._created = bool(payload.get("is_created"))
        container_payload = payload.get("container")
        if container_payload:
            if not isinstance(self.container, RemoteContainerProxy):
                self.container = RemoteContainerProxy(self)
            self.container._refresh(container_payload)
            if not self.container_name:
                self.container_name = self.container.name
        elif self._created:
            self.container = RemoteContainerProxy(self)
        else:
            self.container = None

    @classmethod
    def from_remote_state(cls, payload: dict[str, Any]) -> "DockerSandbox":
        sandbox = cls()
        sandbox._apply_remote_state(payload)
        return sandbox

    async def create(self, session_id: str = None) -> None:
        if self._created:
            return

        start_time = time.perf_counter()
        if self._use_remote_control():
            if not session_id:
                raise RuntimeError("session_id is required for remote sandbox control")
            try:
                payload = await self._control_client.ensure_sandbox(session_id)
                self._apply_remote_state(payload)
                runtime_metrics.increment("sandbox.create.count", tags={"mode": "remote", "status": "success"})
                runtime_metrics.record_duration(
                    "sandbox.create.duration_seconds",
                    time.perf_counter() - start_time,
                    tags={"mode": "remote"},
                )
                return
            except Exception:
                runtime_metrics.increment("sandbox.create.count", tags={"mode": "remote", "status": "failed"})
                raise

        try:
            await self._ensure_image()

            timestamp = int(time.time() * 1000)
            self.container_name = f"deepeye-sandbox-{timestamp}"
            self.session_id = session_id
            self.volume_name = f"deepeye-ws-{session_id}" if session_id else f"deepeye-ws-{timestamp}"
            volume_existed = await self._ensure_volume()

            labels = {
                "app": "deepeye",
                "component": "sandbox",
                "volume": self.volume_name,
            }
            if session_id:
                labels["session_id"] = session_id

            self.container = self.docker_client.containers.run(**self._build_container_run_kwargs(labels))
            self._created = True
            await self._wait_until_ready()

            if volume_existed:
                logger.info(f"[DockerSandbox] Created: {self.container_name} (reused volume {self.volume_name})")
            else:
                logger.info(f"[DockerSandbox] Created: {self.container_name} (new volume {self.volume_name})")
            runtime_metrics.increment("sandbox.create.count", tags={"mode": "local", "status": "success"})
            runtime_metrics.record_duration(
                "sandbox.create.duration_seconds",
                time.perf_counter() - start_time,
                tags={"mode": "local"},
            )

        except DockerException as e:
            self._created = False
            runtime_metrics.increment("sandbox.create.count", tags={"mode": "local", "status": "failed"})
            raise RuntimeError(f"Failed to create sandbox: {e}")

    async def stop(self) -> None:
        if not self._created or not self.container:
            return

        if self._use_remote_control():
            if not self.session_id:
                return
            payload = await self._control_client.stop_sandbox(self.session_id)
            if payload:
                state = await self._control_client.get_sandbox(self.session_id)
                if state:
                    self._apply_remote_state(state)
            logger.info(f"[DockerSandbox] Stopped: {self.container_name} (data preserved)")
            return

        try:
            self.container.stop(timeout=5)
            logger.info(f"[DockerSandbox] Stopped: {self.container_name} (data preserved)")
        except NotFound:
            pass
        except Exception as e:
            logger.error(f"[DockerSandbox] Error stopping container: {e}")

    async def start(self) -> None:
        if not self._created or not self.container:
            raise RuntimeError("Container not created")

        if self._use_remote_control():
            if not self.session_id:
                raise RuntimeError("Container session_id not set")
            payload = await self._control_client.start_sandbox(self.session_id)
            self._apply_remote_state(payload)
            logger.info(f"[DockerSandbox] Started: {self.container_name}")
            return

        try:
            self.container.start()
            await self._wait_until_ready()
            logger.info(f"[DockerSandbox] Started: {self.container_name}")
        except Exception as e:
            raise RuntimeError(f"Failed to start container: {e}")

    async def restart(self) -> None:
        await self.stop()
        await self.start()
        logger.info(f"[DockerSandbox] Restarted: {self.container_name}")

    async def destroy(self) -> None:
        if not self._created:
            return

        if self._use_remote_control():
            if self.session_id:
                await self._control_client.destroy_sandbox(self.session_id, delete_data=False)
            self._created = False
            self.container = None
            return

        try:
            if self.container:
                try:
                    self.container.stop(timeout=5)
                    self.container.remove(force=True)
                    logger.info(
                        f"[DockerSandbox] Destroyed container: {self.container_name} (volume {self.volume_name} preserved)"
                    )
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
        if self._use_remote_control():
            if self.session_id:
                await self._control_client.destroy_sandbox(self.session_id, delete_data=True)
            self._created = False
            self.container = None
            return

        await self.destroy()
        if self.volume_name:
            try:
                volume = self.docker_client.volumes.get(self.volume_name)
                volume.remove(force=True)
                logger.info(f"[DockerSandbox] Deleted volume: {self.volume_name}")
            except NotFound:
                pass
            except Exception as e:
                logger.error(f"[DockerSandbox] Error deleting volume {self.volume_name}: {e}")

    async def exec_command(self, command: str) -> CommandResult:
        if not self._created or not self.container:
            raise RuntimeError("Sandbox not created. Call create() first.")

        start_time = time.time()

        if self._use_remote_control():
            if not self.session_id:
                raise RuntimeError("Sandbox session_id not set")
            try:
                payload = await self._control_client.exec_sandbox_command(self.session_id, command)
                result = CommandResult(**payload)
                runtime_metrics.increment(
                    "sandbox.exec.count",
                    tags={"mode": "remote", "status": "success" if result.exit_code == 0 else "failed"},
                )
                runtime_metrics.record_duration(
                    "sandbox.exec.duration_seconds",
                    result.execution_time_ms / 1000,
                    tags={"mode": "remote"},
                )
                return result
            except Exception as e:
                execution_time_ms = int((time.time() - start_time) * 1000)
                runtime_metrics.increment("sandbox.exec.count", tags={"mode": "remote", "status": "failed"})
                return CommandResult(
                    stdout="",
                    stderr=f"Command execution error: {str(e)}",
                    exit_code=-1,
                    execution_time_ms=execution_time_ms,
                )

        try:
            exit_code, output = self.container.exec_run(
                cmd=self._build_exec_command(command),
                demux=True,
                workdir="/workspace",
            )

            stdout = output[0].decode("utf-8") if output[0] else ""
            stderr = output[1].decode("utf-8") if output[1] else ""

            execution_time_ms = int((time.time() - start_time) * 1000)
            runtime_metrics.increment(
                "sandbox.exec.count",
                tags={"mode": "local", "status": "success" if exit_code == 0 else "failed"},
            )
            runtime_metrics.record_duration(
                "sandbox.exec.duration_seconds",
                execution_time_ms / 1000,
                tags={"mode": "local"},
            )

            return CommandResult(
                stdout=stdout,
                stderr=stderr,
                exit_code=exit_code,
                execution_time_ms=execution_time_ms,
            )

        except Exception as e:
            execution_time_ms = int((time.time() - start_time) * 1000)
            runtime_metrics.increment("sandbox.exec.count", tags={"mode": "local", "status": "failed"})
            return CommandResult(
                stdout="",
                stderr=f"Command execution error: {str(e)}",
                exit_code=-1,
                execution_time_ms=execution_time_ms,
            )

    async def write_file(self, path: str, data: bytes) -> None:
        if not self._created or not self.container:
            raise RuntimeError("Sandbox not created")

        if self._use_remote_control():
            if not self.session_id:
                raise RuntimeError("Sandbox session_id not set")
            await self._control_client.write_sandbox_file(self.session_id, path, data)
            return

        tar_stream = io.BytesIO()
        with tarfile.open(fileobj=tar_stream, mode="w") as tar:
            tarinfo = tarfile.TarInfo(name=os.path.basename(path))
            tarinfo.size = len(data)
            tar.addfile(tarinfo, io.BytesIO(data))

        tar_stream.seek(0)

        dir_path = os.path.dirname(path)
        if dir_path and dir_path != "/":
            result = await self.exec_command(f"mkdir -p {shlex.quote(dir_path)}")
            if result.exit_code != 0:
                raise RuntimeError(result.stderr or "failed to create sandbox directory")

        if not self.container.put_archive(dir_path or "/", tar_stream):
            raise RuntimeError(f"failed to write file to sandbox: {path}")

    async def write_text_file(self, path: str, content: str, encoding: str = "utf-8") -> None:
        await self.write_file(path, content.encode(encoding))

    async def health_check(self) -> bool:
        if self._use_remote_control():
            if not self.session_id:
                return False
            payload = await self._control_client.get_sandbox(self.session_id)
            if not payload:
                return False
            self._apply_remote_state(payload)
            return bool(payload.get("is_running"))
        return self.is_running()

    def is_running(self) -> bool:
        if not self._created or not self.container:
            return False

        try:
            self.container.reload()
            return self.container.status == "running"
        except Exception:
            return False

    @property
    def is_created(self) -> bool:
        return self._created

    async def __aenter__(self):
        await self.create()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.destroy()

    async def _ensure_volume(self) -> bool:
        try:
            self.docker_client.volumes.get(self.volume_name)
            logger.debug(f"[DockerSandbox] Reusing existing volume: {self.volume_name}")
            return True
        except NotFound:
            self.docker_client.volumes.create(
                name=self.volume_name,
                labels={
                    "app": "deepeye",
                    "component": "sandbox-data",
                    "session_id": self.session_id or "",
                },
            )
            logger.debug(f"[DockerSandbox] Created new volume: {self.volume_name}")
            return False

    async def _ensure_image(self) -> None:
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
        build_context, dockerfile_name, dockerfile_path = resolve_docker_build_target(
            dockerfile_setting=settings.SANDBOX_DOCKERFILE,
            default_context_root=settings.SANDBOX_BUILD_CONTEXT,
            anchor_file=__file__,
        )
        if not dockerfile_path.exists():
            raise RuntimeError(f"Sandbox Dockerfile not found: {dockerfile_path}")
        logger.info(
            "[DockerSandbox] Building image %s from %s (context=%s)",
            settings.SANDBOX_IMAGE,
            dockerfile_path,
            build_context,
        )
        try:
            image, build_logs = self.docker_client.images.build(
                path=build_context,
                dockerfile=dockerfile_name,
                tag=settings.SANDBOX_IMAGE,
                rm=True,
                forcerm=True,
            )
            del image
            for log in build_logs:
                if "stream" in log:
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
        for _ in range(max_retries):
            try:
                if await self.health_check():
                    return
                await asyncio.sleep(interval)
            except Exception:
                await asyncio.sleep(interval)

        raise RuntimeError(f"Container did not become ready in {max_retries * interval}s")
