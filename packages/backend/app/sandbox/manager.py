"""Sandbox Manager - Manage sandbox lifecycle with persistence"""

import asyncio
import shlex
from collections import defaultdict
from typing import Any, Dict, List

from docker.errors import NotFound

from deepeye.sandbox import CommandResult
from deepeye.utils.logger import logger
from app.core.config import settings
from app.sandbox.activity import ActivityTracker
from app.sandbox.cleanup import cleanup_idle_session, collect_cleanup_sessions
from app.sandbox.control_plane import build_remote_sandbox, get_local_docker_client, use_remote_control
from app.sandbox.datasource_sync import (
    DATASOURCE_SYNC_MANIFEST_PATH,
    build_datasource_manifest_entry,
    is_datasource_sync_current,
    load_datasource_sync_manifest,
    write_datasource_sync_manifest,
)
from app.sandbox.docker_sandbox import DockerSandbox
from app.sandbox.docker_discovery import (
    find_containers_by_session,
    list_all_volumes,
    reconnect_to_container,
)
from app.sandbox.factory import create_sandbox
from app.sandbox.session_status import build_manager_stats, build_session_status
from app.datasource.services.specs import get_datasource_filename, workspace_data_path
from app.infra.services.docker_control import get_docker_control_client
from app.infra.services.minio import download_bytes


def _get_datasource_filename(ds) -> str:
    return get_datasource_filename(getattr(ds, "name", None), getattr(ds, "storage_path", None))


_DATASOURCE_SYNC_MANIFEST_PATH = DATASOURCE_SYNC_MANIFEST_PATH


class SandboxManager:
    """
    Manage sandbox instances with Named Volume persistence and auto-cleanup.
    
    Features:
    - Track sandboxes by session_id (supports multiple containers per session)
    - Named Volume persistence (data survives container destruction)
    - Cross-process container discovery via Docker labels
    - Create/destroy sandboxes (containers only, volumes preserved)
    - Auto-stop idle sandboxes
    - Singleton pattern
    
    Data Persistence:
    - Each session gets a Named Volume: deepeye-ws-{session_id}
    - Volume persists across container recreations
    - Data only deleted with destroy_session(delete_data=True)
    
    Docker Labels:
    - app=deepeye
    - component=sandbox
    - session_id={session_id}
    - volume={volume_name}
    """

    _instance = None
    _lock = asyncio.Lock()

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        
        # session_id -> list of sandboxes (in-memory cache)
        self._sandboxes: Dict[str, List[DockerSandbox]] = defaultdict(list)

        self._control_client = get_docker_control_client()
        self._docker = None
        
        # Activity tracking
        self._activity = ActivityTracker()
        self._session_locks: dict[str, asyncio.Lock] = {}
        
        # Background cleanup task
        self._cleanup_task = None
        self._running = False
        
        self._initialized = True

    def _use_remote_control(self) -> bool:
        return use_remote_control()

    def _get_docker_client(self):
        """Create the Docker client only when local sandbox operations need it."""
        self._docker = get_local_docker_client(self._docker)
        return self._docker

    def _build_remote_sandbox(self, payload: dict[str, Any]) -> DockerSandbox:
        return build_remote_sandbox(payload)

    async def get_or_create_sandbox(
        self,
        session_id: str
    ) -> DockerSandbox:
        """
        Get existing sandbox or create new one for the session.
        
        This is the recommended method for most use cases.
        It ensures sandbox reuse within a session.
        
        Args:
            session_id: Session ID

        Returns:
            Sandbox instance (existing or newly created)
        """
        session_lock = self._session_locks.setdefault(session_id, asyncio.Lock())
        async with session_lock:
            # First, try to get existing sandbox
            sandbox = await self.get_sandbox(session_id)
            if sandbox:
                logger.info(f"[SandboxManager] Reusing existing sandbox for {session_id}: {sandbox.container_name}")
                # IMPORTANT: Record activity when reusing sandbox, especially after restart
                self._activity.record_activity(session_id)
                return sandbox

            # No existing sandbox, create new one
            logger.info(f"[SandboxManager] No existing sandbox for {session_id}, creating new one")
            return await self.create_for_session(session_id)
    
    async def create_for_session(self, session_id: str) -> DockerSandbox:
        """
        Create a NEW sandbox for the session (always creates new container).
        
        NOTE: Use get_or_create_sandbox() if you want to reuse existing sandbox.
        
        With Named Volumes:
        - Volume (deepeye-ws-{session_id}) is auto-created or reused
        - If volume exists, data is immediately available (no restore needed!)
        Args:
            session_id: Session ID
            
        Returns:
            Created sandbox instance
        """
        async with self._lock:
            sandbox = create_sandbox()
            # Pass session_id for Docker label and volume naming
            await sandbox.create(session_id=session_id)
            
            self._sandboxes[session_id].append(sandbox)
            self._activity.record_activity(session_id)
            
            logger.info(f"[SandboxManager] Created sandbox for {session_id}: {sandbox.container_name} (volume: {sandbox.volume_name})")
            
            return sandbox

    async def sync_datasource_files(self, session_id: str, file_datasources: list) -> None:
        """
        Sync file-based data sources from MinIO to the sandbox.
        
        Args:
            session_id: Session ID
            file_datasources: List of DataSource objects (category='file')
        """
        sandbox = await self.get_or_create_sandbox(session_id)
        manifest = await load_datasource_sync_manifest(sandbox)
        manifest_updated = False
        
        for ds in file_datasources:
            if ds.category != 'file' or not ds.storage_path:
                logger.warning(f"[SandboxManager] Skipping datasource {ds.id}: category={ds.category}, storage_path={ds.storage_path}")
                continue
            
            logger.info(f"[SandboxManager] Syncing file datasource {ds.name} (id={ds.id}) to sandbox {session_id}")
            logger.info(f"[SandboxManager] Storage path: {ds.storage_path}, Name: {ds.name}")
            
            try:
                manifest_key = str(ds.id)
                manifest_entry = build_datasource_manifest_entry(_get_datasource_filename, ds)

                if await is_datasource_sync_current(
                    sandbox=sandbox,
                    manifest=manifest,
                    manifest_key=manifest_key,
                    manifest_entry=manifest_entry,
                ):
                    logger.info(
                        "[SandboxManager] Skipping sync for %s (id=%s): sandbox copy is up to date",
                        ds.name,
                        ds.id,
                    )
                    continue

                # Download from MinIO
                logger.info(f"[SandboxManager] Downloading from MinIO bucket: {settings.MINIO_DATA_BUCKET}, path: {ds.storage_path}")
                data = download_bytes(settings.MINIO_DATA_BUCKET, ds.storage_path)
                logger.info(f"[SandboxManager] Downloaded {len(data)} bytes")
                
                # Use consistent filename extraction
                original_filename = _get_datasource_filename(ds)
                dest_path = workspace_data_path(original_filename)
                logger.info(f"[SandboxManager] Writing to sandbox path: {dest_path} (from name: {ds.name}, storage_path: {ds.storage_path})")
                await sandbox.write_file(dest_path, data)
                
                # Verify file was written
                result = await sandbox.exec_command(
                    f"test -f {shlex.quote(dest_path)} && echo 'EXISTS' || echo 'NOT_FOUND'"
                )
                if 'EXISTS' in result.stdout:
                    logger.info(f"[SandboxManager] ✅ Successfully synced {ds.name} to {dest_path} ({len(data)} bytes)")
                    manifest[manifest_key] = manifest_entry
                    manifest_updated = True
                else:
                    logger.error(f"[SandboxManager] ❌ File write appeared to succeed but file not found at {dest_path}")
                    logger.error(f"[SandboxManager] Command result: stdout={result.stdout}, stderr={result.stderr}, exit_code={result.exit_code}")
                    
            except Exception as e:
                logger.error(f"[SandboxManager] ❌ Failed to sync file datasource {ds.name} (id={ds.id}): {e}", exc_info=True)
                # Re-raise to prevent silent failures
                raise RuntimeError(f"Failed to sync datasource {ds.name} to sandbox: {e}") from e

        if manifest_updated:
            await write_datasource_sync_manifest(sandbox, manifest)
        self._activity.record_activity(session_id)

    async def remove_datasource_file(self, session_id: str, datasource) -> None:
        """Remove a synced datasource file and clear its manifest entry."""
        sandbox = await self.get_or_create_sandbox(session_id)
        filename = _get_datasource_filename(datasource)
        dest_path = workspace_data_path(filename)
        await sandbox.exec_command(f"rm -f -- {shlex.quote(dest_path)}")

        manifest = await load_datasource_sync_manifest(sandbox)
        if manifest.pop(str(datasource.id), None) is not None:
            await write_datasource_sync_manifest(sandbox, manifest)
        self._activity.record_activity(session_id)
    
    async def get_sandbox(self, session_id: str, index: int = 0) -> DockerSandbox | None:
        """
        Get sandbox by session_id and index.
        
        Cross-process aware: If not in local cache, queries Docker daemon
        for containers with matching session_id label.
        
        Args:
            session_id: Session ID
            index: Sandbox index (default: 0)
            
        Returns:
            Sandbox instance or None
        """
        if self._use_remote_control():
            async with self._lock:
                sandboxes = self._sandboxes.get(session_id, [])
                if index < len(sandboxes):
                    sandbox = sandboxes[index]
                    if await sandbox.health_check():
                        return sandbox
                    logger.warning(
                        f"[SandboxManager] Cached remote sandbox {sandbox.container_name} is no longer healthy, removing from cache"
                    )
                    self._sandboxes[session_id].pop(index)

                payload = await self._control_client.get_sandbox(session_id)
                if not payload:
                    return None

                sandbox = self._build_remote_sandbox(payload)
                self._sandboxes[session_id] = [sandbox]
                self._activity.record_activity(session_id)
                return sandbox

        async with self._lock:
            sandboxes = self._sandboxes.get(session_id, [])
            if index < len(sandboxes):
                sandbox = sandboxes[index]
                # CRITICAL FIX: Verify container still exists and is healthy
                if await sandbox.health_check():
                    return sandbox
                else:
                    logger.warning(f"[SandboxManager] Cached sandbox {sandbox.container_name} is no longer healthy, removing from cache")
                    self._sandboxes[session_id].pop(index)
            
            # Not in local cache or cache was stale - query Docker directly by label
            docker_client = self._get_docker_client()
            containers = find_containers_by_session(docker_client, session_id)
            if containers and index < len(containers):
                container = containers[index]
                container_name = container.name
                logger.info(f"[SandboxManager] Reconnecting to {container_name} for session {session_id}")
                
                # Reconnect to existing container
                try:
                    sandbox = await reconnect_to_container(container)
                    self._sandboxes[session_id].append(sandbox)
                    
                    # Update activity on reconnection
                    self._activity.record_activity(session_id)
                    
                    return sandbox
                except Exception as e:
                    logger.error(f"[SandboxManager] Failed to reconnect to {container_name}: {e}")
                    return None
            
            return None

    async def list_sandboxes(self, session_id: str) -> List[DockerSandbox]:
        """
        List all sandboxes for session.
        
        Args:
            session_id: Session ID
            
        Returns:
            List of sandbox instances
        """
        async with self._lock:
            return self._sandboxes.get(session_id, []).copy()

    async def exec_command(
        self, 
        session_id: str, 
        command: str,
        sandbox_index: int = 0
    ) -> CommandResult:
        """
        Execute command in sandbox and record activity.
        
        Args:
            session_id: Session ID
            command: Command to execute
            sandbox_index: Sandbox index (default: 0)
            
        Returns:
            Command result
            
        Raises:
            RuntimeError: If no sandbox found
        """
        sandbox = await self.get_sandbox(session_id, sandbox_index)
        if not sandbox:
            raise RuntimeError(f"No sandbox found for session {session_id}")
        
        self._activity.record_activity(session_id)
        
        return await sandbox.exec_command(command)

    async def stop_session(self, session_id: str) -> None:
        """
        Stop all sandboxes for session (preserve data).
        
        Args:
            session_id: Session ID
        """
        if self._use_remote_control():
            await self._control_client.stop_sandbox(session_id)
            sandbox = await self.get_sandbox(session_id)
            if sandbox:
                self._sandboxes[session_id] = [sandbox]
            return

        async with self._lock:
            sandboxes = self._sandboxes.get(session_id, [])
            for sandbox in sandboxes:
                try:
                    await sandbox.stop()
                    logger.info(f"[SandboxManager] Stopped sandbox {id(sandbox)} for {session_id}")
                except Exception as e:
                    logger.error(f"[SandboxManager] Error stopping sandbox: {e}")

    async def start_session(self, session_id: str) -> None:
        """
        Start all stopped sandboxes for session.
        
        Args:
            session_id: Session ID
        """
        if self._use_remote_control():
            payload = await self._control_client.start_sandbox(session_id)
            self._sandboxes[session_id] = [self._build_remote_sandbox(payload)]
            self._activity.record_activity(session_id)
            return

        async with self._lock:
            sandboxes = self._sandboxes.get(session_id, [])
            for sandbox in sandboxes:
                try:
                    await sandbox.start()
                    logger.info(f"[SandboxManager] Started sandbox {id(sandbox)} for {session_id}")
                except Exception as e:
                    logger.error(f"[SandboxManager] Error starting sandbox: {e}")
        
        # Record activity after starting
        self._activity.record_activity(session_id)

    async def restart_session(self, session_id: str) -> None:
        """
        Restart all sandboxes for session.
        
        Args:
            session_id: Session ID
        """
        if self._use_remote_control():
            await self._control_client.stop_sandbox(session_id)
            payload = await self._control_client.start_sandbox(session_id)
            self._sandboxes[session_id] = [self._build_remote_sandbox(payload)]
            self._activity.record_activity(session_id)
            return

        async with self._lock:
            sandboxes = self._sandboxes.get(session_id, [])
            for sandbox in sandboxes:
                try:
                    if hasattr(sandbox, 'restart') and callable(sandbox.restart):
                        await sandbox.restart()
                    else:
                        await sandbox.stop()
                        await sandbox.start()
                    logger.info(f"[SandboxManager] Restarted sandbox {id(sandbox)} for {session_id}")
                except Exception as e:
                    logger.error(f"[SandboxManager] Error restarting sandbox: {e}")
        
        # Record activity after restarting
        self._activity.record_activity(session_id)

    async def destroy_session(self, session_id: str, delete_data: bool = False) -> None:
        """
        Destroy all sandboxes for session (containers only by default).
        
        Args:
            session_id: Session ID
            delete_data: If True, also delete the Named Volume (all data lost!)
        """
        if self._use_remote_control():
            await self._control_client.destroy_sandbox(session_id, delete_data=delete_data)
            self._sandboxes.pop(session_id, None)
            self._activity.clear(session_id)
            return

        async with self._lock:
            # First, destroy sandboxes in local cache
            sandboxes = self._sandboxes.pop(session_id, [])
            destroyed_names = set()
            volume_name = None
            
            for sandbox in sandboxes:
                try:
                    container_name = sandbox.container_name
                    volume_name = sandbox.volume_name  # Remember for later
                    
                    if delete_data:
                        await sandbox.destroy_with_data()
                    else:
                        await sandbox.destroy()
                    
                    destroyed_names.add(container_name)
                    logger.info(f"[SandboxManager] Destroyed sandbox {container_name} for {session_id}")
                except Exception as e:
                    logger.error(f"[SandboxManager] Error destroying sandbox: {e}")
            
            # Also destroy any containers in Docker not in local cache
            docker_client = self._get_docker_client()
            containers = find_containers_by_session(docker_client, session_id)
            for container in containers:
                if container.name not in destroyed_names:
                    try:
                        container.stop(timeout=5)
                        container.remove(force=True)
                        logger.info(f"[SandboxManager] Destroyed orphan container {container.name}")
                    except Exception as e:
                        logger.error(f"[SandboxManager] Error destroying orphan container: {e}")
            
            # Delete volume if requested and we know the volume name
            if delete_data:
                volume_name = volume_name or f"deepeye-ws-{session_id}"
                try:
                    volume = docker_client.volumes.get(volume_name)
                    volume.remove(force=True)
                    logger.info(f"[SandboxManager] Deleted volume {volume_name}")
                except NotFound:
                    pass
                except Exception as e:
                    logger.error(f"[SandboxManager] Error deleting volume {volume_name}: {e}")
        
        self._activity.clear(session_id)

    async def cleanup_all(self) -> None:
        """Cleanup all sandboxes"""
        if self._use_remote_control():
            await self._control_client.cleanup_all_sandboxes()
            self._sandboxes.clear()
            return

        async with self._lock:
            sessions = list(self._sandboxes.keys())
        
        for session_id in sessions:
            await self.destroy_session(session_id)
        
        logger.info("[SandboxManager] Cleaned up all sandboxes")

    def get_stats(self) -> dict:
        """
        Get manager statistics.
        
        Returns:
            Stats dict with session counts, sandbox counts, and volume counts
        """
        if self._use_remote_control():
            stats = self._control_client.get_sandbox_stats_sync()
            stats["cleanup_running"] = bool(stats.get("cleanup_running"))
            return stats

        return build_manager_stats(
            sandboxes_by_session=self._sandboxes,
            docker_client=self._get_docker_client(),
            activity=self._activity,
            cleanup_running=self._running,
        )

    def get_session_status(self, session_id: str) -> dict:
        """
        Get status for specific session.
        
        Args:
            session_id: Session ID
            
        Returns:
            Status dict with local and Docker information
        """
        if self._use_remote_control():
            return self._control_client.get_sandbox_status_sync(session_id)

        return build_session_status(
            session_id=session_id,
            sandboxes_by_session=self._sandboxes,
            docker_client=self._get_docker_client(),
            activity=self._activity,
        )
    
    def list_all_volumes(self) -> list[dict]:
        """
        List all deepeye workspace volumes.
        
        Returns:
            List of volume info dicts
        """
        return list_all_volumes(self._get_docker_client())
    
    async def sync_from_docker(self, session_id: str) -> int:
        """
        Sync sandboxes from Docker to local cache.
        
        Useful when a worker process needs to access sandboxes
        created by another process.
        
        Args:
            session_id: Session ID
            
        Returns:
            Number of sandboxes reconnected
        """
        if self._use_remote_control():
            payload = await self._control_client.sync_sandbox_from_docker(session_id)
            sandbox_payload = await self._control_client.get_sandbox(session_id)
            if sandbox_payload:
                self._sandboxes[session_id] = [self._build_remote_sandbox(sandbox_payload)]
                self._activity.record_activity(session_id)
            return int(payload.get("reconnected", 0))

        async with self._lock:
            containers = find_containers_by_session(self._get_docker_client(), session_id)
            if not containers:
                return 0
            
            # Get already cached containers
            existing_sandboxes = self._sandboxes.get(session_id, [])
            existing_names = {s.container_name for s in existing_sandboxes}
            
            # Reconnect to new containers
            reconnected = 0
            for container in containers:
                if container.name not in existing_names:
                    logger.info(f"[SandboxManager] Syncing {container.name} from Docker")
                    try:
                        sandbox = await reconnect_to_container(container)
                        self._sandboxes[session_id].append(sandbox)
                        reconnected += 1
                    except Exception as e:
                        logger.error(f"[SandboxManager] Failed to sync {container.name}: {e}")
            
            if reconnected > 0:
                self._activity.record_activity(session_id)
                logger.info(f"[SandboxManager] Synced {reconnected} sandboxes for {session_id}")
            
        return reconnected

    async def _run_cleanup_cycle(self) -> None:
        """Run one cleanup cycle for idle or orphaned sessions."""
        async with self._lock:
            sessions = list(self._sandboxes.keys())

        sessions = collect_cleanup_sessions(
            cached_sessions=sessions,
            docker_client=self._get_docker_client(),
            activity=self._activity,
        )

        for session_id in sessions:
            try:
                await cleanup_idle_session(
                    session_id=session_id,
                    sandboxes_by_session=self._sandboxes,
                    activity=self._activity,
                    idle_timeout=settings.SANDBOX_IDLE_TIMEOUT,
                    destroy_timeout=settings.SANDBOX_DESTROY_TIMEOUT,
                    destroy_session=self.destroy_session,
                )
            except Exception as e:
                logger.error(f"[SandboxManager] Error processing {session_id}: {e}")

    async def _cleanup_idle_sessions(self) -> None:
        """
        Background task to cleanup idle sessions.
        
        Runs every SANDBOX_CLEANUP_INTERVAL seconds.
        Checks all sessions and:
        - Stops idle sandboxes (> SANDBOX_IDLE_TIMEOUT)
        - Destroys very idle sandboxes (> SANDBOX_DESTROY_TIMEOUT)
        
        Also discovers orphaned containers from Docker (e.g., after restart).
        """
        logger.info("[SandboxManager] Starting cleanup task")
        
        while self._running:
            try:
                await asyncio.sleep(settings.SANDBOX_CLEANUP_INTERVAL)
                await self._run_cleanup_cycle()
            except Exception as e:
                logger.error(f"[SandboxManager] Cleanup error: {e}")
        
        logger.info("[SandboxManager] Cleanup task stopped")

    def start_cleanup_task(self) -> None:
        """Start background cleanup task"""
        if self._use_remote_control():
            self._control_client.start_sandbox_cleanup_sync()
            self._running = True
            return

        if not self._running:
            self._running = True
            self._cleanup_task = asyncio.create_task(self._cleanup_idle_sessions())
            logger.info("[SandboxManager] Cleanup task started")

    async def stop_cleanup_task(self) -> None:
        """Stop background cleanup task"""
        if self._use_remote_control():
            self._control_client.stop_sandbox_cleanup_sync()
            self._running = False
            return

        if self._running:
            self._running = False
            if self._cleanup_task:
                await self._cleanup_task
            logger.info("[SandboxManager] Cleanup task stopped")


# Singleton instance
sandbox_manager = SandboxManager()
