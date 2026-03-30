"""Tests for dashboard preview runtime hardening."""

import json
import os

os.environ.setdefault("ALLOW_INSECURE_DEFAULTS", "true")
os.environ.setdefault("LLM_API_KEY", "test-key")
os.environ.setdefault("LLM_BASE_URL", "http://localhost:8000")
os.environ.setdefault("LLM_MODEL", "test-model")

from app.core.config import settings
from app.services.dashboard_deploy_service import (
    _dashboard_container_environment,
    _resolve_dashboard_cors_origins,
)


def test_resolve_dashboard_cors_origins_filters_wildcards_and_trailing_slashes(monkeypatch) -> None:
    monkeypatch.setattr(
        settings,
        "BACKEND_CORS_ORIGINS",
        ["http://example.com/", "http://localhost:5173", "*"],
    )

    assert _resolve_dashboard_cors_origins() == [
        "http://example.com",
        "http://localhost:5173",
    ]


def test_resolve_dashboard_cors_origins_falls_back_for_empty_allowlist(monkeypatch) -> None:
    monkeypatch.setattr(settings, "BACKEND_CORS_ORIGINS", ["*"])

    assert _resolve_dashboard_cors_origins() == [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]


def test_dashboard_container_environment_serializes_filtered_cors_origins(monkeypatch) -> None:
    monkeypatch.setattr(settings, "BACKEND_CORS_ORIGINS", ["http://example.com/", "*"])

    environment = _dashboard_container_environment()

    assert json.loads(environment["BACKEND_CORS_ORIGINS"]) == ["http://example.com"]
