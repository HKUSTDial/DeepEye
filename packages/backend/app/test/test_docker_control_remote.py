import asyncio
import base64
import io
import os

os.environ.setdefault("ALLOW_INSECURE_DEFAULTS", "true")
os.environ.setdefault("LLM_API_KEY", "test-key")
os.environ.setdefault("LLM_BASE_URL", "http://localhost:8000")
os.environ.setdefault("LLM_MODEL", "test-model")

from app.core.config import settings
from app.sandbox import docker_sandbox as docker_sandbox_module
from app.sandbox import manager as manager_module


class _FakeDockerControlClient:
    def __init__(self) -> None:
        self.writes: list[tuple[str, str, bytes]] = []
        self.archives: list[tuple[str, str, bytes]] = []
        self.created_sessions: set[str] = set()
        self.destroyed: list[tuple[str, bool]] = []

    def _state(self, session_id: str) -> dict:
        return {
            "session_id": session_id,
            "container_name": f"deepeye-sandbox-{session_id}",
            "volume_name": f"deepeye-ws-{session_id}",
            "is_created": True,
            "is_running": True,
            "container": {
                "name": f"deepeye-sandbox-{session_id}",
                "status": "running",
                "labels": {"session_id": session_id, "volume": f"deepeye-ws-{session_id}"},
                "attrs": {"NetworkSettings": {"Networks": {}}},
            },
        }

    async def ensure_sandbox(self, session_id: str) -> dict:
        self.created_sessions.add(session_id)
        return self._state(session_id)

    async def get_sandbox(self, session_id: str) -> dict | None:
        if session_id not in self.created_sessions:
            return None
        return self._state(session_id)

    async def exec_sandbox_command(self, session_id: str, command: str) -> dict:
        return {
            "stdout": f"ran:{session_id}:{command}",
            "stderr": "",
            "exit_code": 0,
            "execution_time_ms": 7,
        }

    async def write_sandbox_file(self, session_id: str, path: str, data: bytes) -> None:
        self.writes.append((session_id, path, data))

    async def start_sandbox(self, session_id: str) -> dict:
        self.created_sessions.add(session_id)
        return self._state(session_id)

    async def stop_sandbox(self, session_id: str) -> dict:
        return {"status": "ok"}

    async def destroy_sandbox(self, session_id: str, *, delete_data: bool = False) -> dict:
        self.destroyed.append((session_id, delete_data))
        self.created_sessions.discard(session_id)
        return {"status": "ok"}

    async def sync_sandbox_from_docker(self, session_id: str) -> dict:
        return {"reconnected": 1 if session_id in self.created_sessions else 0}

    def container_state(self, session_id: str) -> dict:
        return self._state(session_id)["container"]

    def container_exec(self, session_id: str, *, cmd, demux: bool = False, workdir: str | None = None) -> dict:
        del cmd, workdir
        if demux:
            return {
                "exit_code": 0,
                "stdout_base64": base64.b64encode(b"stdout").decode("ascii"),
                "stderr_base64": base64.b64encode(b"stderr").decode("ascii"),
            }
        return {
            "exit_code": 0,
            "output_base64": base64.b64encode(f"output:{session_id}".encode("utf-8")).decode("ascii"),
        }

    def container_put_archive(self, session_id: str, path: str, archive_bytes: bytes) -> None:
        self.archives.append((session_id, path, archive_bytes))

    def container_logs(self, session_id: str) -> bytes:
        return f"logs:{session_id}".encode("utf-8")

    def get_sandbox_status_sync(self, session_id: str) -> dict:
        return {
            "session_id": session_id,
            "cached_sandboxes": 1,
            "docker_containers": 1,
            "container_names": [f"deepeye-sandbox-{session_id}"],
            "volume_name": f"deepeye-ws-{session_id}",
            "has_volume": True,
            "idle_seconds": 0.0,
            "should_stop": False,
            "should_destroy": False,
        }

    def get_sandbox_stats_sync(self) -> dict:
        return {
            "total_sessions": len(self.created_sessions),
            "total_sandboxes_cached": len(self.created_sessions),
            "total_containers_docker": len(self.created_sessions),
            "total_volumes": len(self.created_sessions),
            "activity": {},
            "cleanup_running": False,
        }

    def start_sandbox_cleanup_sync(self) -> dict:
        return {"status": "ok"}

    def stop_sandbox_cleanup_sync(self) -> dict:
        return {"status": "ok"}

    async def cleanup_all_sandboxes(self) -> dict:
        self.created_sessions.clear()
        return {"status": "ok"}


def test_remote_docker_sandbox_proxies_exec_file_and_container_ops(monkeypatch) -> None:
    client = _FakeDockerControlClient()
    monkeypatch.setattr(settings, "DOCKER_CONTROL_MODE", "remote")
    monkeypatch.setattr(docker_sandbox_module, "get_docker_control_client", lambda: client)

    sandbox = docker_sandbox_module.DockerSandbox()
    asyncio.run(sandbox.create("session-1"))

    result = asyncio.run(sandbox.exec_command("echo hello"))
    assert result.stdout == "ran:session-1:echo hello"

    asyncio.run(sandbox.write_file("/workspace/test.txt", b"hello"))
    assert client.writes == [("session-1", "/workspace/test.txt", b"hello")]

    exec_result = sandbox.container.exec_run(["bash", "-lc", "pwd"], demux=True, workdir="/workspace")
    exit_code, output = exec_result
    assert exit_code == 0
    assert output == (b"stdout", b"stderr")

    sandbox.container.put_archive("/workspace", io.BytesIO(b"tar-bytes"))
    assert client.archives == [("session-1", "/workspace", b"tar-bytes")]
    assert sandbox.container.logs() == b"logs:session-1"


def test_remote_sandbox_manager_uses_control_plane_for_lifecycle(monkeypatch) -> None:
    client = _FakeDockerControlClient()
    monkeypatch.setattr(settings, "DOCKER_CONTROL_MODE", "remote")
    monkeypatch.setattr(docker_sandbox_module, "get_docker_control_client", lambda: client)
    monkeypatch.setattr(manager_module, "get_docker_control_client", lambda: client)
    monkeypatch.setattr(manager_module, "create_sandbox", lambda: docker_sandbox_module.DockerSandbox())

    manager_module.SandboxManager._instance = None
    mgr = manager_module.SandboxManager()

    sandbox = asyncio.run(mgr.get_or_create_sandbox("session-2"))
    assert sandbox.container_name == "deepeye-sandbox-session-2"

    stats = mgr.get_stats()
    assert stats["total_sessions"] == 1
    assert mgr.get_session_status("session-2")["has_volume"] is True

    asyncio.run(mgr.destroy_session("session-2", delete_data=True))
    assert client.destroyed == [("session-2", True)]

    manager_module.SandboxManager._instance = None
