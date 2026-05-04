from __future__ import annotations

import io
import json
import os
import tarfile
from pathlib import Path

import pytest

os.environ.setdefault("ALLOW_INSECURE_DEFAULTS", "true")
os.environ.setdefault("LLM_API_KEY", "test-key")
os.environ.setdefault("LLM_BASE_URL", "http://localhost:8000")
os.environ.setdefault("LLM_MODEL", "test-model")

from app.core.config import settings
from app.deploy.services import dashboard as dashboard_module
from app.deploy.services.dashboard import (
    _DASHBOARD_IMAGE_SOURCE_HASH_LABEL,
    _compute_file_sha256,
    _dashboard_container_environment,
    _dashboard_image_source_hash,
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


class _FakeControlClient:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    async def deploy_dashboard_preview(
        self,
        *,
        task_id: str,
        source_archive_bytes: bytes,
        session_id: str | None = None,
    ) -> dict[str, object]:
        self.calls.append(
            {
                "task_id": task_id,
                "source_archive_bytes": source_archive_bytes,
                "session_id": session_id,
            }
        )
        return {"status": "running", "url": f"/dashboards/{task_id}/"}


@pytest.mark.anyio
async def test_remote_dashboard_deploy_uploads_source_archive(monkeypatch, tmp_path: Path) -> None:
    fake_control_client = _FakeControlClient()
    va_app = tmp_path / "va_app"
    (va_app / "public" / "charts").mkdir(parents=True)
    (va_app / "app.py").write_text("app = object()\n", encoding="utf-8")
    (va_app / "public" / "charts" / "chart.html").write_text("<html>chart</html>\n", encoding="utf-8")

    monkeypatch.setattr(settings, "DOCKER_CONTROL_MODE", "remote")
    monkeypatch.setattr(dashboard_module, "get_docker_control_client", lambda: fake_control_client)

    service = dashboard_module.DashboardDeployService()
    result = await service.deploy(task_id="task-1", local_va_app_path=str(va_app))

    assert result == {"status": "running", "url": "/dashboards/task-1/"}
    assert len(fake_control_client.calls) == 1
    payload = fake_control_client.calls[0]
    assert payload["task_id"] == "task-1"
    assert payload["session_id"] is None

    archive_bytes = payload["source_archive_bytes"]
    assert isinstance(archive_bytes, bytes)
    with tarfile.open(fileobj=io.BytesIO(archive_bytes), mode="r:") as tar:
        names = set(tar.getnames())

    assert "app.py" in names
    assert "public/charts/chart.html" in names


def test_dashboard_image_source_hash_reads_image_label() -> None:
    image = type(
        "FakeImage",
        (),
        {
            "attrs": {
                "Config": {
                    "Labels": {
                        _DASHBOARD_IMAGE_SOURCE_HASH_LABEL: "abc123",
                    }
                }
            }
        },
    )()

    assert _dashboard_image_source_hash(image) == "abc123"


def test_ensure_dashboard_image_rebuilds_when_dockerfile_hash_changes(monkeypatch, tmp_path: Path) -> None:
    dockerfile_path = tmp_path / "Dockerfile.dashboard"
    dockerfile_path.write_text("FROM python:3.11-slim\nRUN pip install websockets\n", encoding="utf-8")
    expected_hash = _compute_file_sha256(dockerfile_path)

    class _FakeImages:
        def __init__(self) -> None:
            self.build_calls: list[dict[str, object]] = []
            self.image = type("FakeImage", (), {"attrs": {"Config": {"Labels": {}}}})()

        def get(self, tag: str):
            assert tag == settings.DASHBOARD_IMAGE
            return self.image

        def build(self, **kwargs):
            self.build_calls.append(kwargs)
            return (object(), [])

    fake_images = _FakeImages()
    service = dashboard_module.DashboardDeployService()
    service.docker_client = type("FakeDockerClient", (), {"images": fake_images})()

    monkeypatch.setattr(settings, "DASHBOARD_AUTO_BUILD", True)
    monkeypatch.setattr(
        dashboard_module,
        "_resolve_dashboard_build_target",
        lambda: (str(tmp_path), dockerfile_path.name, dockerfile_path),
    )

    service._ensure_dashboard_image()

    assert len(fake_images.build_calls) == 1
    assert fake_images.build_calls[0]["labels"] == {
        _DASHBOARD_IMAGE_SOURCE_HASH_LABEL: expected_hash,
    }


def test_ensure_dashboard_image_skips_rebuild_for_matching_hash(monkeypatch, tmp_path: Path) -> None:
    dockerfile_path = tmp_path / "Dockerfile.dashboard"
    dockerfile_path.write_text("FROM python:3.11-slim\nRUN pip install websockets\n", encoding="utf-8")
    expected_hash = _compute_file_sha256(dockerfile_path)

    class _FakeImages:
        def __init__(self) -> None:
            self.build_calls: list[dict[str, object]] = []
            self.image = type(
                "FakeImage",
                (),
                {
                    "attrs": {
                        "Config": {
                            "Labels": {
                                _DASHBOARD_IMAGE_SOURCE_HASH_LABEL: expected_hash,
                            }
                        }
                    }
                },
            )()

        def get(self, tag: str):
            assert tag == settings.DASHBOARD_IMAGE
            return self.image

        def build(self, **kwargs):
            self.build_calls.append(kwargs)
            return (object(), [])

    fake_images = _FakeImages()
    service = dashboard_module.DashboardDeployService()
    service.docker_client = type("FakeDockerClient", (), {"images": fake_images})()

    monkeypatch.setattr(settings, "DASHBOARD_AUTO_BUILD", True)
    monkeypatch.setattr(
        dashboard_module,
        "_resolve_dashboard_build_target",
        lambda: (str(tmp_path), dockerfile_path.name, dockerfile_path),
    )

    service._ensure_dashboard_image()

    assert fake_images.build_calls == []
