from __future__ import annotations

import docker
from docker.errors import NotFound

from deepeye.utils.logger import logger

from app.sandbox.docker_sandbox import DockerSandbox


def volume_exists(docker_client: docker.DockerClient | None, volume_name: str) -> bool:
    if not docker_client:
        return False
    try:
        docker_client.volumes.get(volume_name)
        return True
    except NotFound:
        return False


def find_volumes_by_session(docker_client: docker.DockerClient | None, session_id: str) -> list:
    if not docker_client:
        return []
    try:
        return docker_client.volumes.list(filters={"label": f"session_id={session_id}"})
    except Exception as exc:
        logger.error(f"[SandboxManager] Error finding volumes: {exc}")
        return []


def list_all_volumes(docker_client: docker.DockerClient | None) -> list[dict]:
    if not docker_client:
        return []
    try:
        volumes = docker_client.volumes.list(filters={"label": "app=deepeye"})
        return [
            {
                "name": volume.name,
                "session_id": volume.attrs.get("Labels", {}).get("session_id", ""),
                "created": volume.attrs.get("CreatedAt", ""),
            }
            for volume in volumes
        ]
    except Exception as exc:
        logger.error(f"[SandboxManager] Error listing volumes: {exc}")
        return []


def find_containers_by_session(docker_client: docker.DockerClient | None, session_id: str) -> list:
    if not docker_client:
        return []
    try:
        return docker_client.containers.list(
            all=True,
            filters={
                "label": [
                    "app=deepeye",
                    "component=sandbox",
                    f"session_id={session_id}",
                ]
            },
        )
    except Exception as exc:
        logger.error(f"[SandboxManager] Error finding containers for {session_id}: {exc}")
        return []


def find_all_sandbox_containers(docker_client: docker.DockerClient | None) -> list:
    if not docker_client:
        return []
    try:
        return docker_client.containers.list(
            all=True,
            filters={"label": ["app=deepeye", "component=sandbox"]},
        )
    except Exception as exc:
        logger.error(f"[SandboxManager] Error finding all containers: {exc}")
        return []


def discover_docker_sessions(docker_client: docker.DockerClient | None) -> list[str]:
    discovered_sessions: list[str] = []
    for container in find_all_sandbox_containers(docker_client):
        session_id = container.labels.get("session_id")
        if session_id and session_id not in discovered_sessions:
            discovered_sessions.append(session_id)
    return discovered_sessions


async def reconnect_to_container(container) -> DockerSandbox:
    try:
        sandbox = DockerSandbox()
        sandbox.container = container
        sandbox.container_name = container.name
        sandbox.session_id = container.labels.get("session_id")
        sandbox.volume_name = container.labels.get("volume")
        sandbox._created = True

        container.reload()
        if container.status != "running":
            logger.warning(f"[SandboxManager] Container {container.name} is not running, starting it")
            await sandbox.start()

        logger.info(
            f"[SandboxManager] Successfully reconnected to {container.name} (volume: {sandbox.volume_name})"
        )
        return sandbox
    except NotFound as exc:
        raise RuntimeError(f"Container {container.name} not found") from exc
    except Exception as exc:
        raise RuntimeError(f"Failed to reconnect to {container.name}: {exc}") from exc
