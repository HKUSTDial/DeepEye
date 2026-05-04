from __future__ import annotations

import json
import os
import shlex
from types import SimpleNamespace

import pytest

os.environ.setdefault("ALLOW_INSECURE_DEFAULTS", "true")
os.environ.setdefault("LLM_API_KEY", "test-key")
os.environ.setdefault("LLM_BASE_URL", "http://localhost:8000")
os.environ.setdefault("LLM_MODEL", "test-model")

from app.sandbox.manager import SandboxManager, _DATASOURCE_SYNC_MANIFEST_PATH, _get_datasource_filename
from app.datasource.services.specs import workspace_data_path


class _FakeResult(SimpleNamespace):
    def __init__(self, stdout: str = "", stderr: str = "", exit_code: int = 0) -> None:
        super().__init__(stdout=stdout, stderr=stderr, exit_code=exit_code)


class _FakeSyncSandbox:
    def __init__(self) -> None:
        self.files: dict[str, bytes] = {}

    async def write_file(self, path: str, data: bytes) -> None:
        self.files[path] = data

    async def exec_command(self, command: str):
        if command.startswith("cat ") and command.strip().endswith(_DATASOURCE_SYNC_MANIFEST_PATH):
            data = self.files.get(_DATASOURCE_SYNC_MANIFEST_PATH)
            if data is None:
                return _FakeResult(stderr="not found", exit_code=1)
            return _FakeResult(stdout=data.decode("utf-8"))

        if command.startswith("mkdir -p ") and _DATASOURCE_SYNC_MANIFEST_PATH in command:
            payload = command.split("<<'EOF'\n", 1)[1].rsplit("\nEOF", 1)[0]
            self.files[_DATASOURCE_SYNC_MANIFEST_PATH] = payload.encode("utf-8")
            return _FakeResult()

        if command.startswith("test -f "):
            target = shlex.split(command.split("&&", 1)[0])[2]
            exists = target in self.files
            return _FakeResult(stdout="EXISTS\n" if exists else "NOT_FOUND\n")

        if command.startswith("rm -f -- "):
            target = shlex.split(command)[3]
            self.files.pop(target, None)
            return _FakeResult()

        raise AssertionError(f"Unexpected command: {command}")


@pytest.mark.anyio
async def test_sync_datasource_files_skips_unchanged_sandbox_copy(monkeypatch) -> None:
    manager = SandboxManager()
    sandbox = _FakeSyncSandbox()

    async def _get_or_create_sandbox(session_id: str):
        assert session_id == "session-1"
        return sandbox

    downloads: list[str] = []

    def _download_bytes(bucket: str, path: str) -> bytes:
        assert bucket
        downloads.append(path)
        return b"city,revenue\nShanghai,120\n"

    monkeypatch.setattr(manager, "get_or_create_sandbox", _get_or_create_sandbox)
    monkeypatch.setattr("app.sandbox.manager.download_bytes", _download_bytes)

    datasource_v1 = SimpleNamespace(
        id="ds-1",
        category="file",
        storage_path="uploads/clients-v1.csv",
        name="clients.csv",
    )

    await manager.sync_datasource_files("session-1", [datasource_v1])
    await manager.sync_datasource_files("session-1", [datasource_v1])

    assert downloads == ["uploads/clients-v1.csv"]

    expected_path = workspace_data_path(_get_datasource_filename(datasource_v1))
    assert sandbox.files[expected_path].startswith(b"city,revenue")
    manifest = json.loads(sandbox.files[_DATASOURCE_SYNC_MANIFEST_PATH].decode("utf-8"))
    assert manifest["ds-1"]["storage_path"] == "uploads/clients-v1.csv"

    datasource_v2 = SimpleNamespace(
        id="ds-1",
        category="file",
        storage_path="uploads/clients-v2.csv",
        name="clients.csv",
    )
    await manager.sync_datasource_files("session-1", [datasource_v2])

    assert downloads == ["uploads/clients-v1.csv", "uploads/clients-v2.csv"]
    manifest = json.loads(sandbox.files[_DATASOURCE_SYNC_MANIFEST_PATH].decode("utf-8"))
    assert manifest["ds-1"]["storage_path"] == "uploads/clients-v2.csv"


@pytest.mark.anyio
async def test_remove_datasource_file_clears_manifest_entry(monkeypatch) -> None:
    manager = SandboxManager()
    sandbox = _FakeSyncSandbox()
    datasource = SimpleNamespace(
        id="ds-2",
        category="file",
        storage_path="uploads/report.csv",
        name="report.csv",
    )
    target_path = workspace_data_path(_get_datasource_filename(datasource))
    sandbox.files[target_path] = b"col\n1\n"
    sandbox.files[_DATASOURCE_SYNC_MANIFEST_PATH] = json.dumps(
        {
            "ds-2": {
                "storage_path": "uploads/report.csv",
                "filename": "report.csv",
                "dest_path": target_path,
            }
        }
    ).encode("utf-8")

    async def _get_or_create_sandbox(session_id: str):
        assert session_id == "session-2"
        return sandbox

    monkeypatch.setattr(manager, "get_or_create_sandbox", _get_or_create_sandbox)

    await manager.remove_datasource_file("session-2", datasource)

    assert target_path not in sandbox.files
    manifest = json.loads(sandbox.files[_DATASOURCE_SYNC_MANIFEST_PATH].decode("utf-8"))
    assert manifest == {}
