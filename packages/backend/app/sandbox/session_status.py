from __future__ import annotations

from app.core.config import settings
from app.sandbox.activity import ActivityTracker
from app.sandbox.docker_discovery import (
    find_all_sandbox_containers,
    find_containers_by_session,
    list_all_volumes,
    volume_exists,
)


def build_manager_stats(
    *,
    sandboxes_by_session: dict[str, list],
    docker_client,
    activity: ActivityTracker,
    cleanup_running: bool,
) -> dict:
    total_sessions = len(sandboxes_by_session)
    total_sandboxes = sum(len(sandboxes) for sandboxes in sandboxes_by_session.values())
    all_containers = find_all_sandbox_containers(docker_client)
    all_volumes = list_all_volumes(docker_client)
    activity_stats = activity.get_stats()

    return {
        "total_sessions": total_sessions,
        "total_sandboxes_cached": total_sandboxes,
        "total_containers_docker": len(all_containers),
        "total_volumes": len(all_volumes),
        "activity": activity_stats,
        "cleanup_running": cleanup_running,
    }


def build_session_status(
    *,
    session_id: str,
    sandboxes_by_session: dict[str, list],
    docker_client,
    activity: ActivityTracker,
) -> dict:
    sandboxes = sandboxes_by_session.get(session_id, [])
    idle_time = activity.get_idle_time(session_id)
    docker_containers = find_containers_by_session(docker_client, session_id)
    volume_name = f"deepeye-ws-{session_id}"

    return {
        "session_id": session_id,
        "cached_sandboxes": len(sandboxes),
        "docker_containers": len(docker_containers),
        "container_names": [container.name for container in docker_containers],
        "volume_name": volume_name,
        "has_volume": volume_exists(docker_client, volume_name),
        "idle_seconds": idle_time.total_seconds(),
        "should_stop": activity.should_stop(session_id, settings.SANDBOX_IDLE_TIMEOUT),
        "should_destroy": activity.should_stop(session_id, settings.SANDBOX_DESTROY_TIMEOUT),
    }
