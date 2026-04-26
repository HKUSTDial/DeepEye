"""Sandbox control-plane helpers."""

from __future__ import annotations

from typing import Any

import docker

from app.core.config import settings
from app.sandbox.docker_sandbox import DockerSandbox


def use_remote_control() -> bool:
    return settings.DOCKER_CONTROL_MODE == "remote"


def get_local_docker_client(current_client: docker.DockerClient | None) -> docker.DockerClient | None:
    """Return a lazily-created Docker client for local control mode."""
    if use_remote_control():
        return None
    return current_client or docker.from_env()


def build_remote_sandbox(payload: dict[str, Any]) -> DockerSandbox:
    return DockerSandbox.from_remote_state(payload)
