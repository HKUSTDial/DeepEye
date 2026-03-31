from __future__ import annotations

import os

import pytest

os.environ.setdefault("ALLOW_INSECURE_DEFAULTS", "true")
os.environ.setdefault("LLM_API_KEY", "test-key")
os.environ.setdefault("LLM_BASE_URL", "http://localhost:8000")
os.environ.setdefault("LLM_MODEL", "test-model")

from app.runtime_control import main as runtime_control_main
from deepeye.sandbox import CommandResult


class _FakeSandbox:
    def __init__(self) -> None:
        self.commands: list[str] = []

    async def exec_command(self, command: str) -> CommandResult:
        self.commands.append(command)
        return CommandResult(
            stdout="ok\n",
            stderr="",
            exit_code=0,
            execution_time_ms=12,
        )


@pytest.mark.anyio
async def test_exec_sandbox_command_serializes_dataclass_result(monkeypatch) -> None:
    sandbox = _FakeSandbox()

    async def _get_or_create_sandbox(session_id: str):
        assert session_id == "session-1"
        return sandbox

    monkeypatch.setattr(runtime_control_main.sandbox_manager, "get_or_create_sandbox", _get_or_create_sandbox)

    result = await runtime_control_main.exec_sandbox_command(
        "session-1",
        runtime_control_main.CommandRequest(command="pwd"),
    )

    assert sandbox.commands == ["pwd"]
    assert result == {
        "stdout": "ok\n",
        "stderr": "",
        "exit_code": 0,
        "success": True,
        "execution_time_ms": 12,
    }
