from __future__ import annotations

import base64
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


@pytest.mark.anyio
async def test_deploy_dashboard_preview_decodes_uploaded_archive(monkeypatch) -> None:
    captured: dict[str, object] = {}

    async def _deploy(
        task_id: str,
        local_va_app_path: str | None = None,
        source_archive_bytes: bytes | None = None,
        session_id: str | None = None,
    ):
        captured["task_id"] = task_id
        captured["local_va_app_path"] = local_va_app_path
        captured["source_archive_bytes"] = source_archive_bytes
        captured["session_id"] = session_id
        return {"status": "running", "url": "/dashboards/demo/"}

    monkeypatch.setattr(runtime_control_main.dashboard_deployer, "deploy", _deploy)

    result = await runtime_control_main.deploy_dashboard_preview(
        runtime_control_main.DashboardDeployRequest(
            task_id="task-1",
            source_archive_base64=base64.b64encode(b"dashboard-archive").decode("ascii"),
            session_id="session-1",
        )
    )

    assert result == {"status": "running", "url": "/dashboards/demo/"}
    assert captured == {
        "task_id": "task-1",
        "local_va_app_path": None,
        "source_archive_bytes": b"dashboard-archive",
        "session_id": "session-1",
    }


@pytest.mark.anyio
async def test_cleanup_session_previews_delegates_to_preview_manager(monkeypatch) -> None:
    captured: list[str] = []

    async def _cleanup(session_id: str) -> None:
        captured.append(session_id)

    monkeypatch.setattr(runtime_control_main.preview_runtime_manager, "cleanup_session_previews", _cleanup)

    result = await runtime_control_main.cleanup_session_previews("session-9")

    assert result == {"status": "ok"}
    assert captured == ["session-9"]
