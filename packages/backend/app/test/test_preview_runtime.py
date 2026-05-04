from __future__ import annotations

import os
import time
from types import SimpleNamespace

os.environ.setdefault("ALLOW_INSECURE_DEFAULTS", "true")
os.environ.setdefault("LLM_API_KEY", "test-key")
os.environ.setdefault("LLM_BASE_URL", "http://localhost:8000")
os.environ.setdefault("LLM_MODEL", "test-model")

from app.runtime.services.preview import preview_container_labels, preview_containers_to_cleanup


def _container(name: str, *, status: str, created_at_epoch: int):
    return SimpleNamespace(
        name=name,
        status=status,
        labels={"created_at_epoch": str(created_at_epoch)},
        attrs={},
    )


def test_preview_container_labels_include_runtime_metadata() -> None:
    labels = preview_container_labels(preview_kind="video", task_id="task-1", session_id="session-1")

    assert labels["app"] == "deepeye"
    assert labels["component"] == "preview-runtime"
    assert labels["preview_kind"] == "video"
    assert labels["task_id"] == "task-1"
    assert labels["session_id"] == "session-1"
    assert int(labels["created_at_epoch"]) <= int(time.time())


def test_preview_containers_to_cleanup_removes_stopped_expired_and_overflowing_containers() -> None:
    now = 2_000
    containers = [
        _container("stopped", status="exited", created_at_epoch=1_990),
        _container("expired", status="running", created_at_epoch=1_000),
        _container("fresh-1", status="running", created_at_epoch=1_999),
        _container("fresh-2", status="running", created_at_epoch=1_998),
        _container("fresh-3", status="running", created_at_epoch=1_997),
    ]

    cleanup = preview_containers_to_cleanup(
        containers,
        now=now,
        ttl_seconds=300,
        max_running=2,
    )

    assert [container.name for container in cleanup] == [
        "stopped",
        "expired",
        "fresh-3",
    ]
