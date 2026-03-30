from __future__ import annotations

import os
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

os.environ.setdefault("ALLOW_INSECURE_DEFAULTS", "true")
os.environ.setdefault("LLM_API_KEY", "test-key")
os.environ.setdefault("LLM_BASE_URL", "http://localhost:8000")
os.environ.setdefault("LLM_MODEL", "test-model")

from app.api.v1.sandbox import files as sandbox_files_api


class _FakeWriteSandbox:
    def __init__(self) -> None:
        self.writes: list[tuple[str, str]] = []

    async def write_text_file(self, path: str, content: str) -> None:
        self.writes.append((path, content))


class _FakeListSandbox:
    def __init__(self) -> None:
        self.commands: list[str] = []

    async def exec_command(self, command: str):
        self.commands.append(command)
        if command.startswith("test -d "):
            return SimpleNamespace(success=True, stdout="exists\n", stderr="", exit_code=0)
        if command.startswith("find "):
            return SimpleNamespace(
                success=True,
                stdout="\0".join(["odd\tname.txt", "f", "12", "folder", "d", "0", ""]),
                stderr="",
                exit_code=0,
            )
        raise AssertionError(f"Unexpected command: {command}")


@pytest.mark.anyio
async def test_list_files_returns_404_without_creating_sandbox(monkeypatch) -> None:
    async def _get_sandbox(session_id: str):
        assert session_id == "session-1"
        return None

    async def _get_or_create_sandbox(session_id: str):
        raise AssertionError("list_files should not create a sandbox")

    monkeypatch.setattr(sandbox_files_api.sandbox_manager, "get_sandbox", _get_sandbox)
    monkeypatch.setattr(sandbox_files_api.sandbox_manager, "get_or_create_sandbox", _get_or_create_sandbox)

    with pytest.raises(HTTPException) as exc_info:
        await sandbox_files_api.list_files("session-1")

    assert exc_info.value.status_code == 404


@pytest.mark.anyio
async def test_write_file_handles_eof_like_content_without_shell_heredoc(monkeypatch) -> None:
    sandbox = _FakeWriteSandbox()

    async def _get_or_create_sandbox(session_id: str):
        assert session_id == "session-2"
        return sandbox

    monkeypatch.setattr(sandbox_files_api.sandbox_manager, "get_or_create_sandbox", _get_or_create_sandbox)

    payload = sandbox_files_api.FileWriteRequest(
        path="/workspace/notes/odd 'file'.txt",
        content="first line\nEOF\nlast line\n",
    )

    response = await sandbox_files_api.write_file("session-2", payload)

    assert response == {"status": "success", "path": "/workspace/notes/odd 'file'.txt"}
    assert sandbox.writes == [("/workspace/notes/odd 'file'.txt", "first line\nEOF\nlast line\n")]


@pytest.mark.anyio
async def test_list_files_parses_null_delimited_output(monkeypatch) -> None:
    sandbox = _FakeListSandbox()

    async def _get_sandbox(session_id: str):
        assert session_id == "session-3"
        return sandbox

    monkeypatch.setattr(sandbox_files_api.sandbox_manager, "get_sandbox", _get_sandbox)

    response = await sandbox_files_api.list_files("session-3", "/workspace/project")

    assert [file.name for file in response.files] == ["folder", "odd\tname.txt"]
    assert response.files[0].path == "/workspace/project/folder"
    assert response.files[1].path == "/workspace/project/odd\tname.txt"
