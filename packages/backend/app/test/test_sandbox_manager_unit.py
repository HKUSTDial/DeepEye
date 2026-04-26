from __future__ import annotations

import asyncio
import os
from types import SimpleNamespace

import pytest

os.environ.setdefault("ALLOW_INSECURE_DEFAULTS", "true")
os.environ.setdefault("LLM_API_KEY", "test-key")
os.environ.setdefault("LLM_BASE_URL", "http://localhost:8000")
os.environ.setdefault("LLM_MODEL", "test-model")

from app.sandbox import manager as manager_module
from app.sandbox import control_plane as control_plane_module
from app.sandbox.manager import SandboxManager


def test_sandbox_manager_does_not_initialize_docker_client_until_needed(monkeypatch) -> None:
    manager_module.SandboxManager._instance = None

    def _raise_if_called():
        raise AssertionError("docker.from_env should be lazy")

    monkeypatch.setattr(control_plane_module.docker, "from_env", _raise_if_called)

    manager = SandboxManager()

    assert manager._docker is None
    manager_module.SandboxManager._instance = None


@pytest.mark.anyio
async def test_get_or_create_sandbox_serializes_creation(monkeypatch) -> None:
    manager = SandboxManager()
    manager._sandboxes.clear()
    manager._session_locks.clear()

    created = SimpleNamespace(container_name="sandbox-1")
    state: dict[str, object] = {"sandbox": None, "create_calls": 0}

    async def _get_sandbox(session_id: str):
        assert session_id == "session-1"
        await asyncio.sleep(0.01)
        return state["sandbox"]

    async def _create_for_session(session_id: str):
        assert session_id == "session-1"
        state["create_calls"] = int(state["create_calls"]) + 1
        await asyncio.sleep(0.05)
        state["sandbox"] = created
        return created

    monkeypatch.setattr(manager, "get_sandbox", _get_sandbox)
    monkeypatch.setattr(manager, "create_for_session", _create_for_session)

    sandbox_a, sandbox_b = await asyncio.gather(
        manager.get_or_create_sandbox("session-1"),
        manager.get_or_create_sandbox("session-1"),
    )

    assert state["create_calls"] == 1
    assert sandbox_a is created
    assert sandbox_b is created
