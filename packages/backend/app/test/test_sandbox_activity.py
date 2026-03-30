from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from fnmatch import fnmatch
from types import SimpleNamespace

import pytest

os.environ.setdefault("ALLOW_INSECURE_DEFAULTS", "true")
os.environ.setdefault("LLM_API_KEY", "test-key")
os.environ.setdefault("LLM_BASE_URL", "http://localhost:8000")
os.environ.setdefault("LLM_MODEL", "test-model")

from app.core.config import settings
from app.sandbox.activity import ActivityTracker
from app.sandbox.manager import SandboxManager


class _FakeRedis:
    def __init__(self) -> None:
        self.values: dict[str, str] = {}

    def setex(self, key: str, ttl: int, value: str) -> None:
        assert ttl > 0
        self.values[key] = value

    def get(self, key: str) -> str | None:
        return self.values.get(key)

    def delete(self, key: str) -> None:
        self.values.pop(key, None)

    def scan_iter(self, match: str | None = None):
        for key in list(self.values.keys()):
            if match is None or fnmatch(key, match):
                yield key

    def close(self) -> None:
        return None


class _FakeDockerClient:
    def __init__(self, containers: list[SimpleNamespace]) -> None:
        self.containers = SimpleNamespace(list=lambda **kwargs: containers)


class _FakeRunningSandbox:
    def __init__(self) -> None:
        self.is_created = True
        self.stop_calls = 0

    def is_running(self) -> bool:
        return True

    async def stop(self) -> None:
        self.stop_calls += 1


def test_activity_tracker_shares_state_across_instances() -> None:
    redis_client = _FakeRedis()
    tracker_a = ActivityTracker(redis_client=redis_client)
    tracker_b = ActivityTracker(redis_client=redis_client)
    timestamp = datetime.utcnow() - timedelta(seconds=12)

    tracker_a.record_activity("session-1", at=timestamp)

    assert tracker_b.get_last_active("session-1") == timestamp
    assert tracker_b.get_idle_time("session-1") < timedelta(minutes=1)
    assert tracker_b.get_all_sessions() == ["session-1"]


def test_parse_datetime_normalizes_aware_values_to_utc_naive() -> None:
    parsed = ActivityTracker._parse_datetime("2026-03-30T10:15:00+02:00")

    assert parsed == datetime(2026, 3, 30, 8, 15, 0)
    assert parsed.tzinfo is None


@pytest.mark.anyio
async def test_cleanup_cycle_marks_discovered_session_active_when_no_shared_activity(monkeypatch) -> None:
    manager = SandboxManager()
    activity = ActivityTracker(redis_client=_FakeRedis())
    container = SimpleNamespace(labels={"session_id": "orphan-session"}, name="sandbox-orphan")
    destroyed: list[tuple[str, bool]] = []

    manager._sandboxes.clear()
    monkeypatch.setattr(manager, "_activity", activity, raising=False)
    monkeypatch.setattr(manager, "_docker", _FakeDockerClient([container]), raising=False)

    async def _destroy_session(session_id: str, delete_data: bool = False) -> None:
        destroyed.append((session_id, delete_data))

    monkeypatch.setattr(manager, "destroy_session", _destroy_session)
    monkeypatch.setattr(settings, "SANDBOX_DESTROY_TIMEOUT", 1)
    monkeypatch.setattr(settings, "SANDBOX_IDLE_TIMEOUT", 1)

    await manager._run_cleanup_cycle()

    assert destroyed == []
    assert activity.get_last_active("orphan-session") is not None


@pytest.mark.anyio
async def test_cleanup_cycle_destroys_discovered_session_with_stale_shared_activity(monkeypatch) -> None:
    manager = SandboxManager()
    activity = ActivityTracker(redis_client=_FakeRedis())
    stale_time = datetime.utcnow() - timedelta(hours=8)
    container = SimpleNamespace(labels={"session_id": "stale-session"}, name="sandbox-stale")
    destroyed: list[tuple[str, bool]] = []

    manager._sandboxes.clear()
    activity.record_activity("stale-session", at=stale_time)
    activity._activities.clear()

    monkeypatch.setattr(manager, "_activity", activity, raising=False)
    monkeypatch.setattr(manager, "_docker", _FakeDockerClient([container]), raising=False)

    async def _destroy_session(session_id: str, delete_data: bool = False) -> None:
        destroyed.append((session_id, delete_data))

    monkeypatch.setattr(manager, "destroy_session", _destroy_session)
    monkeypatch.setattr(settings, "SANDBOX_DESTROY_TIMEOUT", 1)
    monkeypatch.setattr(settings, "SANDBOX_IDLE_TIMEOUT", 1)

    await manager._run_cleanup_cycle()

    assert destroyed == [("stale-session", False)]


@pytest.mark.anyio
async def test_cleanup_cycle_stops_idle_cached_running_sandbox(monkeypatch) -> None:
    manager = SandboxManager()
    activity = ActivityTracker(redis_client=_FakeRedis())
    sandbox = _FakeRunningSandbox()
    idle_time = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(minutes=5)

    manager._sandboxes.clear()
    manager._sandboxes["idle-session"] = [sandbox]
    monkeypatch.setattr(manager, "_activity", activity, raising=False)
    monkeypatch.setattr(manager, "_docker", _FakeDockerClient([]), raising=False)
    activity.record_activity("idle-session", at=idle_time)
    monkeypatch.setattr(settings, "SANDBOX_IDLE_TIMEOUT", 1)
    monkeypatch.setattr(settings, "SANDBOX_DESTROY_TIMEOUT", 3600)

    await manager._run_cleanup_cycle()

    assert sandbox.stop_calls == 1
