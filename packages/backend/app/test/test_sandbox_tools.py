from __future__ import annotations

import os
from types import SimpleNamespace

import pytest

os.environ.setdefault("ALLOW_INSECURE_DEFAULTS", "true")
os.environ.setdefault("LLM_API_KEY", "test-key")
os.environ.setdefault("LLM_BASE_URL", "http://localhost:8000")
os.environ.setdefault("LLM_MODEL", "test-model")

from app.sandbox.tools import create_bash_tool


class _FakeSandbox:
    async def exec_command(self, command: str):
        return SimpleNamespace(success=True, stdout=f"ran: {command}", stderr="", exit_code=0)


@pytest.mark.anyio
async def test_bash_tool_only_notifies_on_likely_file_mutations() -> None:
    sandbox = _FakeSandbox()
    notifications: list[str] = []
    tool = create_bash_tool(sandbox, lambda: notifications.append("changed"))

    await tool.ainvoke({"command": "ls -la /workspace"})
    await tool.ainvoke({"command": "echo hello > /workspace/output.txt"})

    assert notifications == ["changed"]
