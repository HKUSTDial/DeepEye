from __future__ import annotations

import os

os.environ.setdefault("ALLOW_INSECURE_DEFAULTS", "true")
os.environ.setdefault("LLM_API_KEY", "test-key")
os.environ.setdefault("LLM_BASE_URL", "http://localhost:8000")
os.environ.setdefault("LLM_MODEL", "test-model")

from app.runtime.services import preview_manager as preview_runtime_manager_module


class _FakeContainer:
    def __init__(self, name: str, *, labels: dict[str, str]) -> None:
        self.name = name
        self.labels = labels
        self.removed = False

    def remove(self, force: bool = False) -> None:
        assert force is True
        self.removed = True


class _FakeContainerCollection:
    def __init__(self, containers: list[_FakeContainer]) -> None:
        self._containers = containers

    def list(self, all: bool = False, filters: dict | None = None):
        assert all is True
        labels = set((filters or {}).get("label") or [])
        result = []
        for container in self._containers:
            container_labels = {f"{key}={value}" for key, value in container.labels.items()}
            if labels.issubset(container_labels):
                result.append(container)
        return result


class _FakeDockerClient:
    def __init__(self, containers: list[_FakeContainer]) -> None:
        self.containers = _FakeContainerCollection(containers)


def test_cleanup_session_previews_removes_only_matching_session(monkeypatch) -> None:
    monkeypatch.setattr(preview_runtime_manager_module.settings, "DOCKER_CONTROL_MODE", "local")
    containers = [
        _FakeContainer(
            "video-session-1",
            labels={"component": "preview-runtime", "preview_kind": "video", "session_id": "session-1"},
        ),
        _FakeContainer(
            "dashboard-session-1",
            labels={"component": "preview-runtime", "preview_kind": "dashboard", "session_id": "session-1"},
        ),
        _FakeContainer(
            "video-session-2",
            labels={"component": "preview-runtime", "preview_kind": "video", "session_id": "session-2"},
        ),
    ]
    monkeypatch.setattr(
        preview_runtime_manager_module.docker,
        "from_env",
        lambda: _FakeDockerClient(containers),
    )

    manager = preview_runtime_manager_module.PreviewRuntimeManager()

    import asyncio

    asyncio.run(manager.cleanup_session_previews("session-1"))

    assert containers[0].removed is True
    assert containers[1].removed is True
    assert containers[2].removed is False
