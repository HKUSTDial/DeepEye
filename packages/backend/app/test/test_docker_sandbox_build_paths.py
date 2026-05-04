from __future__ import annotations

import os
from pathlib import Path

import pytest

os.environ.setdefault("ALLOW_INSECURE_DEFAULTS", "true")
os.environ.setdefault("LLM_API_KEY", "test-key")
os.environ.setdefault("LLM_BASE_URL", "http://localhost:8000")
os.environ.setdefault("LLM_MODEL", "test-model")

from app.core.config import settings
from app.infra.services.docker_build_paths import resolve_docker_build_target
from app.sandbox.docker_sandbox import DockerSandbox


class _FakeImageManager:
    def __init__(self) -> None:
        self.build_kwargs: dict[str, object] | None = None

    def build(self, **kwargs):
        self.build_kwargs = kwargs
        return object(), []


class _FakeDockerClient:
    def __init__(self) -> None:
        self.images = _FakeImageManager()


@pytest.mark.anyio
async def test_build_image_resolves_existing_dockerfile_when_default_context_is_wrong(monkeypatch) -> None:
    fake_client = _FakeDockerClient()

    monkeypatch.setattr("app.sandbox.docker_sandbox.docker.from_env", lambda: fake_client)
    monkeypatch.setattr(settings, "DOCKER_CONTROL_MODE", "local")
    monkeypatch.setattr(settings, "SANDBOX_BUILD_CONTEXT", "/tmp/deepeye-missing-build-context")
    monkeypatch.setattr(settings, "SANDBOX_DOCKERFILE", "docker/Dockerfile.sandbox")
    monkeypatch.setattr(settings, "SANDBOX_IMAGE", "deepeye-sandbox:test")

    sandbox = DockerSandbox()

    await sandbox._build_image()

    build_kwargs = fake_client.images.build_kwargs
    assert build_kwargs is not None
    build_context = Path(str(build_kwargs["path"]))
    dockerfile_name = str(build_kwargs["dockerfile"])
    assert dockerfile_name == "docker/Dockerfile.sandbox"
    assert (build_context / dockerfile_name).exists()


def test_build_target_resolves_repo_root_from_nested_service_anchor() -> None:
    nested_anchor = Path(__file__).resolve().parents[1] / "deploy" / "services" / "video.py"

    build_context, dockerfile_name, dockerfile_path = resolve_docker_build_target(
        dockerfile_setting="docker/Dockerfile.video-preview",
        default_context_root="/tmp/deepeye-missing-build-context",
        anchor_file=str(nested_anchor),
    )

    assert dockerfile_name == "docker/Dockerfile.video-preview"
    assert (Path(build_context) / dockerfile_name).exists()
    assert dockerfile_path.name == "Dockerfile.video-preview"
