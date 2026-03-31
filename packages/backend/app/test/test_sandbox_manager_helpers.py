from __future__ import annotations

import os
from datetime import timedelta
from types import SimpleNamespace

import pytest

os.environ.setdefault("ALLOW_INSECURE_DEFAULTS", "true")
os.environ.setdefault("LLM_API_KEY", "test-key")
os.environ.setdefault("LLM_BASE_URL", "http://localhost:8000")
os.environ.setdefault("LLM_MODEL", "test-model")

from app.sandbox import cleanup as cleanup_helpers
from app.sandbox import session_status as status_helpers


class _FakeContainerAPI:
    def __init__(self, containers_by_session: dict[str, list[object]], all_containers: list[object]) -> None:
        self._containers_by_session = containers_by_session
        self._all_containers = all_containers

    def list(self, *, all: bool, filters: dict) -> list[object]:
        del all
        labels = filters.get("label", [])
        if labels == ["app=deepeye", "component=sandbox"]:
            return self._all_containers
        session_labels = [label for label in labels if label.startswith("session_id=")]
        if not session_labels:
            return []
        session_id = session_labels[0].split("=", 1)[1]
        return self._containers_by_session.get(session_id, [])


class _FakeVolumeAPI:
    def __init__(self, volumes: list[object]) -> None:
        self._volumes = volumes

    def list(self, *, filters: dict) -> list[object]:
        del filters
        return self._volumes

    def get(self, volume_name: str):
        for volume in self._volumes:
            if volume.name == volume_name:
                return volume
        from docker.errors import NotFound

        raise NotFound("missing")


class _FakeActivity:
    def __init__(
        self,
        *,
        idle_seconds: float = 0,
        stats: dict | None = None,
        last_active=None,
        should_stop_sequence: list[bool] | None = None,
    ) -> None:
        self.idle_seconds = idle_seconds
        self.stats = stats or {"total_sessions": 1, "average_idle_seconds": idle_seconds}
        self.last_active = last_active
        self.should_stop_sequence = list(should_stop_sequence or [])
        self.recorded: list[str] = []

    def get_stats(self) -> dict:
        return self.stats

    def get_idle_time(self, session_id: str) -> timedelta:
        del session_id
        return timedelta(seconds=self.idle_seconds)

    def should_stop(self, session_id: str, timeout: int) -> bool:
        del session_id, timeout
        if self.should_stop_sequence:
            return self.should_stop_sequence.pop(0)
        return False

    def get_last_active(self, session_id: str):
        del session_id
        return self.last_active

    def record_activity(self, session_id: str) -> None:
        self.recorded.append(session_id)


class _FakeSandbox:
    def __init__(self, *, is_created: bool = True, running: bool = True) -> None:
        self.is_created = is_created
        self._running = running
        self.stop_calls = 0

    def is_running(self) -> bool:
        return self._running

    async def stop(self) -> None:
        self.stop_calls += 1
        self._running = False


def _build_docker_client() -> SimpleNamespace:
    session_containers = {
        "session-a": [SimpleNamespace(name="sandbox-a")],
    }
    all_containers = [
        SimpleNamespace(name="sandbox-a", labels={"session_id": "session-a"}),
        SimpleNamespace(name="sandbox-b", labels={"session_id": "session-b"}),
    ]
    volumes = [
        SimpleNamespace(name="deepeye-ws-session-a", attrs={"Labels": {"session_id": "session-a"}, "CreatedAt": "now"}),
        SimpleNamespace(name="deepeye-ws-session-b", attrs={"Labels": {"session_id": "session-b"}, "CreatedAt": "later"}),
    ]
    return SimpleNamespace(
        containers=_FakeContainerAPI(session_containers, all_containers),
        volumes=_FakeVolumeAPI(volumes),
    )


def test_build_manager_stats_counts_cached_and_discovered_resources() -> None:
    docker_client = _build_docker_client()
    activity = _FakeActivity(idle_seconds=12, stats={"total_sessions": 2, "average_idle_seconds": 12})

    stats = status_helpers.build_manager_stats(
        sandboxes_by_session={"session-a": [object()], "session-b": [object(), object()]},
        docker_client=docker_client,
        activity=activity,
        cleanup_running=True,
    )

    assert stats == {
        "total_sessions": 2,
        "total_sandboxes_cached": 3,
        "total_containers_docker": 2,
        "total_volumes": 2,
        "activity": {"total_sessions": 2, "average_idle_seconds": 12},
        "cleanup_running": True,
    }


def test_build_session_status_reports_idle_and_volume_state() -> None:
    docker_client = _build_docker_client()
    activity = _FakeActivity(idle_seconds=42, should_stop_sequence=[True, False])

    status = status_helpers.build_session_status(
        session_id="session-a",
        sandboxes_by_session={"session-a": [object(), object()]},
        docker_client=docker_client,
        activity=activity,
    )

    assert status == {
        "session_id": "session-a",
        "cached_sandboxes": 2,
        "docker_containers": 1,
        "container_names": ["sandbox-a"],
        "volume_name": "deepeye-ws-session-a",
        "has_volume": True,
        "idle_seconds": 42.0,
        "should_stop": True,
        "should_destroy": False,
    }


def test_collect_cleanup_sessions_records_new_orphan_activity(monkeypatch) -> None:
    activity = _FakeActivity(last_active=None)
    monkeypatch.setattr(cleanup_helpers, "discover_docker_sessions", lambda docker_client: ["session-a", "session-b"])

    sessions = cleanup_helpers.collect_cleanup_sessions(
        cached_sessions=["session-a"],
        docker_client=object(),
        activity=activity,
    )

    assert sessions == ["session-a", "session-b"]
    assert activity.recorded == ["session-b"]


@pytest.mark.anyio
async def test_cleanup_idle_session_stops_running_sandboxes() -> None:
    sandbox = _FakeSandbox(is_created=True, running=True)
    activity = _FakeActivity(should_stop_sequence=[False, True])
    destroyed: list[str] = []

    async def _destroy_session(session_id: str, delete_data: bool = False) -> None:
        destroyed.append(f"{session_id}:{delete_data}")

    await cleanup_helpers.cleanup_idle_session(
        session_id="session-a",
        sandboxes_by_session={"session-a": [sandbox]},
        activity=activity,
        idle_timeout=60,
        destroy_timeout=300,
        destroy_session=_destroy_session,
    )

    assert destroyed == []
    assert sandbox.stop_calls == 1


@pytest.mark.anyio
async def test_cleanup_idle_session_destroys_very_idle_session() -> None:
    activity = _FakeActivity(should_stop_sequence=[True])
    destroyed: list[str] = []

    async def _destroy_session(session_id: str, delete_data: bool = False) -> None:
        destroyed.append(f"{session_id}:{delete_data}")

    await cleanup_helpers.cleanup_idle_session(
        session_id="session-z",
        sandboxes_by_session={"session-z": [_FakeSandbox()]},
        activity=activity,
        idle_timeout=60,
        destroy_timeout=300,
        destroy_session=_destroy_session,
    )

    assert destroyed == ["session-z:False"]
