from __future__ import annotations

import os

import pytest
from docker.errors import NotFound

os.environ.setdefault("ALLOW_INSECURE_DEFAULTS", "true")
os.environ.setdefault("LLM_API_KEY", "test-key")
os.environ.setdefault("LLM_BASE_URL", "http://localhost:8000")
os.environ.setdefault("LLM_MODEL", "test-model")

from app.sandbox.docker_sandbox import DockerSandbox
from app.core.config import settings


class _FakeContainer:
    def __init__(self) -> None:
        self.status = "running"
        self.exec_calls: list[dict[str, object]] = []

    def reload(self) -> None:
        return None

    def exec_run(self, *, cmd, demux, workdir):
        self.exec_calls.append(
            {
                "cmd": cmd,
                "demux": demux,
                "workdir": workdir,
            }
        )
        return 0, (b"ok", b"")

    def stop(self, timeout: int = 5) -> None:
        del timeout

    def remove(self, force: bool = True) -> None:
        del force

    def start(self) -> None:
        self.status = "running"


class _FakeContainerManager:
    def __init__(self, container: _FakeContainer) -> None:
        self._container = container
        self.run_kwargs: dict[str, object] | None = None

    def run(self, **kwargs):
        self.run_kwargs = kwargs
        return self._container


class _FakeVolumeManager:
    def __init__(self) -> None:
        self._volumes: dict[str, object] = {}

    def get(self, name: str):
        if name not in self._volumes:
            raise NotFound("missing volume")
        return self._volumes[name]

    def create(self, *, name: str, labels: dict[str, str]):
        volume = type("Volume", (), {"name": name, "labels": labels})()
        self._volumes[name] = volume
        return volume


class _FakeImageManager:
    def get(self, image: str):
        return type("Image", (), {"tags": [image]})()


class _FakeDockerClient:
    def __init__(self, container: _FakeContainer) -> None:
        self.containers = _FakeContainerManager(container)
        self.volumes = _FakeVolumeManager()
        self.images = _FakeImageManager()


@pytest.mark.anyio
async def test_create_applies_container_security_limits(monkeypatch) -> None:
    fake_container = _FakeContainer()
    fake_client = _FakeDockerClient(fake_container)

    monkeypatch.setattr("app.sandbox.docker_sandbox.docker.from_env", lambda: fake_client)
    monkeypatch.setattr(settings, "SANDBOX_NO_NEW_PRIVILEGES", True)
    monkeypatch.setattr(settings, "SANDBOX_DROP_ALL_CAPABILITIES", True)
    monkeypatch.setattr(settings, "SANDBOX_NETWORK_DISABLED", False)
    monkeypatch.setattr(settings, "SANDBOX_INIT_PROCESS", True)
    monkeypatch.setattr(settings, "SANDBOX_PIDS_LIMIT", 256)
    monkeypatch.setattr(settings, "SANDBOX_MEMORY_LIMIT", "2g")
    monkeypatch.setattr(settings, "SANDBOX_MEMORY_SWAP_LIMIT", "2g")
    monkeypatch.setattr(settings, "SANDBOX_CPU_LIMIT", 1.5)
    monkeypatch.setattr(settings, "SANDBOX_TMPFS_SIZE_MB", 128)

    sandbox = DockerSandbox()

    async def _no_wait(*args, **kwargs):
        del args, kwargs
        return None

    monkeypatch.setattr(sandbox, "_wait_until_ready", _no_wait)

    await sandbox.create(session_id="session-1")

    run_kwargs = fake_client.containers.run_kwargs
    assert run_kwargs is not None
    assert run_kwargs["cap_drop"] == ["ALL"]
    assert run_kwargs["security_opt"] == ["no-new-privileges:true"]
    assert run_kwargs["pids_limit"] == 256
    assert run_kwargs["mem_limit"] == "2g"
    assert run_kwargs["memswap_limit"] == "2g"
    assert run_kwargs["nano_cpus"] == 1_500_000_000
    assert run_kwargs["init"] is True
    assert run_kwargs["network_disabled"] is False
    assert run_kwargs["environment"] == {
        "HOME": "/tmp",
        "XDG_CACHE_HOME": "/tmp/.cache",
        "MPLCONFIGDIR": "/tmp/matplotlib",
        "PIP_DISABLE_PIP_VERSION_CHECK": "1",
        "PIP_NO_CACHE_DIR": "1",
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONUNBUFFERED": "1",
    }
    assert run_kwargs["tmpfs"] == {
        "/tmp": "rw,nosuid,nodev,size=134217728",
        "/run": "rw,nosuid,nodev,size=16777216",
    }
    assert run_kwargs["labels"]["session_id"] == "session-1"


@pytest.mark.anyio
async def test_exec_command_wraps_command_with_timeout(monkeypatch) -> None:
    fake_container = _FakeContainer()
    fake_client = _FakeDockerClient(fake_container)

    monkeypatch.setattr("app.sandbox.docker_sandbox.docker.from_env", lambda: fake_client)
    monkeypatch.setattr(settings, "SANDBOX_EXEC_TIMEOUT_SECONDS", 120)

    sandbox = DockerSandbox()
    sandbox.container = fake_container
    sandbox._created = True

    result = await sandbox.exec_command("python /workspace/task.py")

    assert result.exit_code == 0
    assert fake_container.exec_calls == [
        {
            "cmd": [
                "timeout",
                "--kill-after=12s",
                "120s",
                "bash",
                "-c",
                "python /workspace/task.py",
            ],
            "demux": True,
            "workdir": "/workspace",
        }
    ]
