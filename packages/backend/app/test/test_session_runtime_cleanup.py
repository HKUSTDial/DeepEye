from __future__ import annotations

import os

import pytest

os.environ.setdefault("ALLOW_INSECURE_DEFAULTS", "true")
os.environ.setdefault("LLM_API_KEY", "test-key")
os.environ.setdefault("LLM_BASE_URL", "http://localhost:8000")
os.environ.setdefault("LLM_MODEL", "test-model")

from app.api.v1 import sessions as sessions_api


@pytest.mark.anyio
async def test_cleanup_session_runtime_resources_cleans_sandbox_and_previews(monkeypatch) -> None:
    calls: list[tuple[str, str, bool | None]] = []

    async def _destroy_session(session_id: str, delete_data: bool = False) -> None:
        calls.append(("sandbox", session_id, delete_data))

    async def _cleanup_previews(session_id: str) -> None:
        calls.append(("preview", session_id, None))

    monkeypatch.setattr(sessions_api.sandbox_manager, "destroy_session", _destroy_session)
    monkeypatch.setattr(sessions_api.preview_runtime_manager, "cleanup_session_previews", _cleanup_previews)

    await sessions_api._cleanup_session_runtime_resources("session-42")

    assert calls == [
        ("sandbox", "session-42", True),
        ("preview", "session-42", None),
    ]
