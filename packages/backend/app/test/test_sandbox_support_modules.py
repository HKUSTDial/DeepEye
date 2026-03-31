from __future__ import annotations

import json
import os
from types import SimpleNamespace

import pytest

os.environ.setdefault("ALLOW_INSECURE_DEFAULTS", "true")
os.environ.setdefault("LLM_API_KEY", "test-key")
os.environ.setdefault("LLM_BASE_URL", "http://localhost:8000")
os.environ.setdefault("LLM_MODEL", "test-model")

from app.sandbox import datasource_sync, docker_discovery


class _FakeExecSandbox:
    def __init__(self, result) -> None:
        self._result = result
        self.commands: list[str] = []

    async def exec_command(self, command: str):
        self.commands.append(command)
        return self._result


class _FakeWriteSandbox:
    def __init__(self) -> None:
        self.writes: list[tuple[str, str]] = []

    async def write_text_file(self, path: str, content: str) -> None:
        self.writes.append((path, content))


class _FakeContainerList:
    def __init__(self, containers) -> None:
        self._containers = containers
        self.calls: list[dict] = []

    def list(self, **kwargs):
        self.calls.append(kwargs)
        return self._containers


def test_build_datasource_manifest_entry_uses_workspace_data_path() -> None:
    datasource = SimpleNamespace(name="Sales Report.csv", storage_path="uploads/2026/sales.csv")

    entry = datasource_sync.build_datasource_manifest_entry(lambda ds: ds.name, datasource)

    assert entry == {
        "storage_path": "uploads/2026/sales.csv",
        "filename": "Sales Report.csv",
        "dest_path": "/workspace/data/Sales_Report.csv",
    }


@pytest.mark.anyio
async def test_load_datasource_sync_manifest_ignores_invalid_json() -> None:
    sandbox = _FakeExecSandbox(SimpleNamespace(exit_code=0, stdout="{oops", stderr=""))

    manifest = await datasource_sync.load_datasource_sync_manifest(sandbox)

    assert manifest == {}
    assert sandbox.commands == [f"cat {datasource_sync.DATASOURCE_SYNC_MANIFEST_PATH}"]


@pytest.mark.anyio
async def test_write_datasource_sync_manifest_uses_direct_file_write() -> None:
    sandbox = _FakeWriteSandbox()
    manifest = {
        "1": {
            "storage_path": "uploads/report.csv",
            "filename": "EOF\nreport.csv",
            "dest_path": "/workspace/data/EOF\nreport.csv",
        }
    }

    await datasource_sync.write_datasource_sync_manifest(sandbox, manifest)

    assert sandbox.writes == [
        (
            datasource_sync.DATASOURCE_SYNC_MANIFEST_PATH,
            json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True),
        )
    ]


def test_discover_docker_sessions_deduplicates_session_labels() -> None:
    containers = [
        SimpleNamespace(labels={"session_id": "session-a"}),
        SimpleNamespace(labels={"session_id": "session-a"}),
        SimpleNamespace(labels={"session_id": "session-b"}),
        SimpleNamespace(labels={}),
    ]
    docker_client = SimpleNamespace(containers=_FakeContainerList(containers))

    sessions = docker_discovery.discover_docker_sessions(docker_client)

    assert sessions == ["session-a", "session-b"]


@pytest.mark.anyio
async def test_reconnect_to_container_starts_stopped_container(monkeypatch) -> None:
    starts: list[str] = []

    class _FakeSandbox:
        def __init__(self) -> None:
            self.container = None
            self.container_name = None
            self.session_id = None
            self.volume_name = None
            self._created = False

        async def start(self) -> None:
            starts.append(self.container_name)
            self.container.status = "running"

    class _FakeContainer:
        name = "deepeye-sandbox-1"
        labels = {"session_id": "session-a", "volume": "deepeye-ws-session-a"}
        status = "exited"

        def reload(self) -> None:
            return None

    monkeypatch.setattr(docker_discovery, "DockerSandbox", _FakeSandbox)

    sandbox = await docker_discovery.reconnect_to_container(_FakeContainer())

    assert starts == ["deepeye-sandbox-1"]
    assert sandbox.container_name == "deepeye-sandbox-1"
    assert sandbox.session_id == "session-a"
    assert sandbox.volume_name == "deepeye-ws-session-a"
