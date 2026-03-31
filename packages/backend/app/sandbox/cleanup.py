from __future__ import annotations

from deepeye.utils.logger import logger

from app.sandbox.activity import ActivityTracker
from app.sandbox.docker_discovery import discover_docker_sessions


def collect_cleanup_sessions(
    *,
    cached_sessions: list[str],
    docker_client,
    activity: ActivityTracker,
) -> list[str]:
    sessions = list(cached_sessions)
    for session_id in discover_docker_sessions(docker_client):
        if session_id in sessions:
            continue
        sessions.append(session_id)
        last_active = activity.get_last_active(session_id)
        if last_active is None:
            activity.record_activity(session_id)
            logger.info(
                "[SandboxManager] Discovered orphaned session from Docker without activity state; marking active now: %s",
                session_id,
            )
        else:
            logger.info(f"[SandboxManager] Discovered orphaned session from Docker: {session_id}")
    return sessions


async def cleanup_idle_session(
    *,
    session_id: str,
    sandboxes_by_session: dict[str, list],
    activity: ActivityTracker,
    idle_timeout: int,
    destroy_timeout: int,
    destroy_session,
) -> None:
    if activity.should_stop(session_id, destroy_timeout):
        await destroy_session(session_id, delete_data=False)
        logger.info("[SandboxManager] Auto-destroyed idle %s (idle > %ss)", session_id, destroy_timeout)
        return

    if not activity.should_stop(session_id, idle_timeout):
        return

    sandboxes = sandboxes_by_session.get(session_id, [])
    for sandbox in sandboxes:
        if sandbox.is_created and sandbox.is_running():
            await sandbox.stop()
            logger.info("[SandboxManager] Auto-stopped idle %s (idle > %ss)", session_id, idle_timeout)
