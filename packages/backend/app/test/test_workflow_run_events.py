"""Tests for workflow run event publishing helpers."""

from __future__ import annotations

import asyncio
import json
import os
from types import SimpleNamespace

import pytest

os.environ.setdefault("ALLOW_INSECURE_DEFAULTS", "true")
os.environ.setdefault("LLM_API_KEY", "test-key")
os.environ.setdefault("LLM_BASE_URL", "http://localhost:8000")
os.environ.setdefault("LLM_MODEL", "test-model")

from app.workflow.services.run_events import WorkflowRunEventPublisher


class FakeEventBus:
    def __init__(self) -> None:
        self.published: list[tuple[str, dict]] = []
        self.closed = False

    async def publish(self, channel: str, data: str) -> None:
        self.published.append((channel, json.loads(data)))

    async def close(self) -> None:
        self.closed = True


@pytest.mark.asyncio
async def test_workflow_event_publisher_adds_run_metadata_and_normalizes_artifact() -> None:
    bus = FakeEventBus()
    publisher = WorkflowRunEventPublisher(
        bus,
        "session-1",
        workflow_path="/workspace/workflow/demo.json",
        tracking_refs=lambda: {
            "turn_id": "turn-1",
            "draft_id": "draft-1",
            "run_id": "run-1",
        },
    )

    await publisher.publish_workflow_event(
        "artifact_ready",
        {"artifact": {"kind": "dashboard", "dashboard_url": "/dashboards/demo/"}},
    )

    channel, event = bus.published[-1]
    assert channel == "session:session-1"
    assert event["type"] == "workflow_event"
    assert event["data"]["turn_id"] == "turn-1"
    assert event["data"]["draft_id"] == "draft-1"
    assert event["data"]["run_id"] == "run-1"
    assert event["data"]["metadata"] == {"file_path": "/workspace/workflow/demo.json"}
    assert event["data"]["payload"]["artifact"]["preview"] == {
        "type": "url",
        "url": "/dashboards/demo/",
    }


@pytest.mark.asyncio
async def test_workflow_event_publisher_schedules_progress_and_node_callbacks() -> None:
    bus = FakeEventBus()
    publisher = WorkflowRunEventPublisher(bus, "session-1")
    loop = asyncio.get_running_loop()

    publisher.progress_callback(loop)("Working")
    publisher.node_start_callback(loop)("node-a", SimpleNamespace(status="running"), None)
    publisher.node_end_callback(loop)(
        "node-a",
        SimpleNamespace(status="success", outputs={"rows": [{"city": "Austin"}]}),
        None,
    )

    await asyncio.sleep(0)
    await asyncio.sleep(0)

    events = [event for _, event in bus.published]
    assert events[0]["type"] == "token"
    assert events[0]["data"] == {"content": "Working\n", "source": "workflow"}
    assert events[1]["data"]["phase"] == "node_status"
    assert events[1]["data"]["payload"] == {"node_id": "node-a", "status": "running"}
    assert events[2]["data"]["payload"] == {
        "node_id": "node-a",
        "outputs": {
            "columns": ["city"],
            "preview_rows": [{"city": "Austin"}],
            "row_count": 1,
            "rows": [{"city": "Austin"}],
        },
        "status": "success",
    }
