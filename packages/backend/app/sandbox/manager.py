"""Sandbox Manager - Manage sandbox lifecycle with persistence"""

import asyncio
from typing import Dict, List
from collections import defaultdict

import docker
from docker.errors import NotFound

from deepeye.sandbox import CommandResult
from deepeye.utils.logger import logger
from app.sandbox.docker_sandbox import DockerSandbox
from app.sandbox.factory import create_sandbox
from app.sandbox.activity import ActivityTracker
from app.core.config import settings
from app.services.minio_service import download_bytes


def _get_datasource_filename(ds) -> str:
    """
    Extract the original filename from a datasource object.
    Tries storage_path first (which contains the original filename),
    falls back to ds.name if needed.
    """
    import os
    if ds.storage_path:
        # storage_path format: datasource-files/{user_id}/{datasource_id}/{filename}
        original_filename = os.path.basename(ds.storage_path)
        # Only use if it's different from the full path (i.e., extraction succeeded)
        if original_filename and original_filename != ds.storage_path:
            return original_filename
    # Fallback to ds.name
    return ds.name


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
        
        # Docker client for cross-process container discovery
        self._docker = docker.from_env()
        
        # Activity tracking
        self._activity = ActivityTracker()
        
        # Background cleanup task
        self._cleanup_task = None
        self._running = False
        
        self._initialized = True

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
        # First, try to get existing sandbox
        sandbox = await self.get_sandbox(session_id)
        if sandbox:
            logger.info(f"[SandboxManager] Reusing existing sandbox for {session_id}: {sandbox.container_name}")
            # IMPORTANT: Record activity when reusing sandbox, especially after restart
            self._activity.record_activity(session_id)
            return sandbox
        
        # No existing sandbox, create new one
        logger.info(f"[SandboxManager] No existing sandbox for {session_id}, creating new one")
        sandbox = await self.create_for_session(session_id)
        # Record activity for newly created sandbox
        self._activity.record_activity(session_id)
        return sandbox
    
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
        
        for ds in file_datasources:
            if ds.category != 'file' or not ds.storage_path:
                logger.warning(f"[SandboxManager] Skipping datasource {ds.id}: category={ds.category}, storage_path={ds.storage_path}")
                continue
            
            logger.info(f"[SandboxManager] Syncing file datasource {ds.name} (id={ds.id}) to sandbox {session_id}")
            logger.info(f"[SandboxManager] Storage path: {ds.storage_path}, Name: {ds.name}")
            
            try:
                # Download from MinIO
                logger.info(f"[SandboxManager] Downloading from MinIO bucket: {settings.MINIO_DATA_BUCKET}, path: {ds.storage_path}")
                data = download_bytes(settings.MINIO_DATA_BUCKET, ds.storage_path)
                logger.info(f"[SandboxManager] Downloaded {len(data)} bytes")
                
                # Use consistent filename extraction
                original_filename = _get_datasource_filename(ds)
                dest_path = f"/workspace/data/{original_filename}"
                logger.info(f"[SandboxManager] Writing to sandbox path: {dest_path} (from name: {ds.name}, storage_path: {ds.storage_path})")
                await sandbox.write_file(dest_path, data)
                
                # Verify file was written
                result = await sandbox.exec_command(f"test -f {dest_path} && echo 'EXISTS' || echo 'NOT_FOUND'")
                if 'EXISTS' in result.stdout:
                    logger.info(f"[SandboxManager] ✅ Successfully synced {ds.name} to {dest_path} ({len(data)} bytes)")
                else:
                    logger.error(f"[SandboxManager] ❌ File write appeared to succeed but file not found at {dest_path}")
                    logger.error(f"[SandboxManager] Command result: stdout={result.stdout}, stderr={result.stderr}, exit_code={result.exit_code}")
                    
            except Exception as e:
                logger.error(f"[SandboxManager] ❌ Failed to sync file datasource {ds.name} (id={ds.id}): {e}", exc_info=True)
                # Re-raise to prevent silent failures
                raise RuntimeError(f"Failed to sync datasource {ds.name} to sandbox: {e}") from e
    
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
            containers = self._find_containers_by_session(session_id)
            if containers and index < len(containers):
                container = containers[index]
                container_name = container.name
                logger.info(f"[SandboxManager] Reconnecting to {container_name} for session {session_id}")
                
                # Reconnect to existing container
                try:
                    sandbox = await self._reconnect_to_container(container)
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
            containers = self._find_containers_by_session(session_id)
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
                    volume = self._docker.volumes.get(volume_name)
                    volume.remove(force=True)
                    logger.info(f"[SandboxManager] Deleted volume {volume_name}")
                except NotFound:
                    pass
                except Exception as e:
                    logger.error(f"[SandboxManager] Error deleting volume {volume_name}: {e}")
        
        self._activity.clear(session_id)

    async def cleanup_all(self) -> None:
        """Cleanup all sandboxes"""
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
        total_sessions = len(self._sandboxes)
        total_sandboxes = sum(len(sandboxes) for sandboxes in self._sandboxes.values())
        
        # Count all deepeye sandbox containers in Docker
        all_containers = self._find_all_sandbox_containers()
        
        # Count all deepeye volumes
        all_volumes = self.list_all_volumes()
        
        activity_stats = self._activity.get_stats()
        
        return {
            "total_sessions": total_sessions,
            "total_sandboxes_cached": total_sandboxes,
            "total_containers_docker": len(all_containers),
            "total_volumes": len(all_volumes),
            "activity": activity_stats,
            "cleanup_running": self._running,
        }

    def get_session_status(self, session_id: str) -> dict:
        """
        Get status for specific session.
        
        Args:
            session_id: Session ID
            
        Returns:
            Status dict with local and Docker information
        """
        # Local cache info
        sandboxes = self._sandboxes.get(session_id, [])
        idle_time = self._activity.get_idle_time(session_id)
        # Docker containers (may include containers not in local cache)
        docker_containers = self._find_containers_by_session(session_id)
        
        # Check if volume exists
        volume_name = f"deepeye-ws-{session_id}"
        has_volume = self._volume_exists(volume_name)
        
        status = {
            "session_id": session_id,
            "cached_sandboxes": len(sandboxes),
            "docker_containers": len(docker_containers),
            "container_names": [c.name for c in docker_containers],
            "volume_name": volume_name,
            "has_volume": has_volume,
            "idle_seconds": idle_time.total_seconds(),
            "should_stop": self._activity.should_stop(
                session_id,
                settings.SANDBOX_IDLE_TIMEOUT,
            ),
            "should_destroy": self._activity.should_stop(
                session_id,
                settings.SANDBOX_DESTROY_TIMEOUT,
            ),
        }
        
        return status
    
    def _volume_exists(self, volume_name: str) -> bool:
        """Check if a Docker volume exists."""
        try:
            self._docker.volumes.get(volume_name)
            return True
        except NotFound:
            return False
    
    def _find_volumes_by_session(self, session_id: str) -> list:
        """Find all volumes for a session by label."""
        try:
            volumes = self._docker.volumes.list(
                filters={"label": f"session_id={session_id}"}
            )
            return volumes
        except Exception as e:
            logger.error(f"[SandboxManager] Error finding volumes: {e}")
            return []
    
    def list_all_volumes(self) -> list[dict]:
        """
        List all deepeye workspace volumes.
        
        Returns:
            List of volume info dicts
        """
        try:
            volumes = self._docker.volumes.list(
                filters={"label": "app=deepeye"}
            )
            return [
                {
                    "name": v.name,
                    "session_id": v.attrs.get("Labels", {}).get("session_id", ""),
                    "created": v.attrs.get("CreatedAt", ""),
                }
                for v in volumes
            ]
        except Exception as e:
            logger.error(f"[SandboxManager] Error listing volumes: {e}")
            return []
    
    def _find_containers_by_session(self, session_id: str) -> list:
        """
        Find all Docker containers for a session by label.
        
        Args:
            session_id: Session ID
            
        Returns:
            List of Docker container objects
        """
        try:
            return self._docker.containers.list(
                all=True,  # Include stopped containers
                filters={
                    "label": [
                        "app=deepeye",
                        "component=sandbox",
                        f"session_id={session_id}"
                    ]
                }
            )
        except Exception as e:
            logger.error(f"[SandboxManager] Error finding containers for {session_id}: {e}")
            return []
    
    def _find_all_sandbox_containers(self) -> list:
        """
        Find all deepeye sandbox containers.
        
        Returns:
            List of Docker container objects
        """
        try:
            return self._docker.containers.list(
                all=True,
                filters={
                    "label": [
                        "app=deepeye",
                        "component=sandbox"
                    ]
                }
            )
        except Exception as e:
            logger.error(f"[SandboxManager] Error finding all containers: {e}")
            return []
    
    async def _reconnect_to_container(self, container) -> DockerSandbox:
        """
        Reconnect to an existing Docker container.
        
        Args:
            container: Docker container object
            
        Returns:
            DockerSandbox instance connected to the container
            
        Raises:
            RuntimeError: If container cannot be accessed
        """
        try:
            # Create new sandbox instance
            sandbox = DockerSandbox()
            
            # Manually set the container properties
            sandbox.container = container
            sandbox.container_name = container.name
            sandbox.session_id = container.labels.get("session_id")
            sandbox.volume_name = container.labels.get("volume")  # Get volume from label
            sandbox._created = True
            
            # Check if container is running
            container.reload()
            if container.status != "running":
                logger.warning(f"[SandboxManager] Container {container.name} is not running, starting it")
                await sandbox.start()
            
            logger.info(f"[SandboxManager] Successfully reconnected to {container.name} (volume: {sandbox.volume_name})")
            return sandbox
            
        except NotFound:
            raise RuntimeError(f"Container {container.name} not found")
        except Exception as e:
            raise RuntimeError(f"Failed to reconnect to {container.name}: {e}")
    
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
        async with self._lock:
            containers = self._find_containers_by_session(session_id)
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
                        sandbox = await self._reconnect_to_container(container)
                        self._sandboxes[session_id].append(sandbox)
                        reconnected += 1
                    except Exception as e:
                        logger.error(f"[SandboxManager] Failed to sync {container.name}: {e}")
            
            if reconnected > 0:
                self._activity.record_activity(session_id)
                logger.info(f"[SandboxManager] Synced {reconnected} sandboxes for {session_id}")
            
            return reconnected

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
                
                # Get all active sessions from memory
                async with self._lock:
                    sessions = list(self._sandboxes.keys())
                
                # Also discover sessions from Docker (handles restart scenario)
                try:
                    all_containers = self._docker.containers.list(
                        all=True,
                        filters={"label": ["app=deepeye", "component=sandbox"]}
                    )
                    docker_sessions = set()
                    for container in all_containers:
                        sid = container.labels.get("session_id")
                        if sid:
                            docker_sessions.add(sid)
                    
                    # Add Docker sessions not in memory
                    for sid in docker_sessions:
                        if sid not in sessions:
                            sessions.append(sid)
                            logger.info(f"[SandboxManager] Discovered orphaned session from Docker: {sid}")
                except Exception as e:
                    logger.error(f"[SandboxManager] Error discovering Docker sessions: {e}")
                
                # Process all sessions
                for session_id in sessions:
                    try:
                        # Check if should destroy (very idle)
                        if self._activity.should_stop(session_id, settings.SANDBOX_DESTROY_TIMEOUT):
                            await self.destroy_session(session_id, delete_data=False)
                            logger.info(f"[SandboxManager] Auto-destroyed idle {session_id} (idle > {settings.SANDBOX_DESTROY_TIMEOUT}s)")
                            continue
                        
                        # Check if should stop (idle)
                        if self._activity.should_stop(session_id, settings.SANDBOX_IDLE_TIMEOUT):
                            sandboxes = self._sandboxes.get(session_id, [])
                            for sandbox in sandboxes:
                                if sandbox.is_created and sandbox.is_running():
                                    await sandbox.stop()
                                    logger.info(f"[SandboxManager] Auto-stopped idle {session_id} (idle > {settings.SANDBOX_IDLE_TIMEOUT}s)")
                                    
                    except Exception as e:
                        logger.error(f"[SandboxManager] Error processing {session_id}: {e}")
                        
            except Exception as e:
                logger.error(f"[SandboxManager] Cleanup error: {e}")
        
        logger.info("[SandboxManager] Cleanup task stopped")

    def start_cleanup_task(self) -> None:
        """Start background cleanup task"""
        if not self._running:
            self._running = True
            self._cleanup_task = asyncio.create_task(self._cleanup_idle_sessions())
            logger.info("[SandboxManager] Cleanup task started")

    async def stop_cleanup_task(self) -> None:
        """Stop background cleanup task"""
        if self._running:
            self._running = False
            if self._cleanup_task:
                await self._cleanup_task
            logger.info("[SandboxManager] Cleanup task stopped")


# Singleton instance
sandbox_manager = SandboxManager()
