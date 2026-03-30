"""Sandbox management API endpoints"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.sandbox import sandbox_manager

router = APIRouter(tags=["sandbox-management"])


class StatusResponse(BaseModel):
    """Status response model"""
    session_id: str
    cached_sandboxes: int
    docker_containers: int
    container_names: list[str]
    volume_name: str
    has_volume: bool
    idle_seconds: float
    should_stop: bool
    should_destroy: bool


class StatsResponse(BaseModel):
    """Stats response model"""
    total_sessions: int
    total_sandboxes_cached: int
    total_containers_docker: int
    total_volumes: int
    activity: dict
    cleanup_running: bool


@router.get("/sessions/{session_id}/status", response_model=StatusResponse)
async def get_sandbox_status(session_id: str):
    """
    Get sandbox status for session.
    
    Returns information about:
    - Active sandboxes
    - Idle time
    - Whether should stop
    """
    try:
        status = sandbox_manager.get_session_status(session_id)
        return StatusResponse(**status)
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get status: {str(e)}"
        )


@router.post("/sessions/{session_id}/stop")
async def stop_sandbox(session_id: str):
    """
    Stop sandbox for session (preserve data).
    
    The sandbox can be started again later.
    """
    try:
        await sandbox_manager.stop_session(session_id)
        return {"status": "success", "message": f"Stopped sandbox for {session_id}"}
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Stop failed: {str(e)}"
        )


@router.post("/sessions/{session_id}/start")
async def start_sandbox(session_id: str):
    """
    Start stopped sandbox for session.
    """
    try:
        sandbox = await sandbox_manager.get_or_create_sandbox(session_id)
        return {"status": "success", "message": f"Started sandbox for {session_id}", "container_name": sandbox.container_name}
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Start failed: {str(e)}"
        )


@router.delete("/sessions/{session_id}")
async def destroy_sandbox(session_id: str, delete_data: bool = False):
    """
    Destroy sandbox for session.

    By default only the container is removed and the workspace volume is preserved.
    Set ``delete_data=true`` to permanently delete the volume as well.
    """
    try:
        await sandbox_manager.destroy_session(session_id, delete_data=delete_data)
        if delete_data:
            message = f"Destroyed sandbox and deleted data for {session_id}"
        else:
            message = f"Destroyed sandbox for {session_id} (data preserved)"
        return {"status": "success", "message": message}
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Destroy failed: {str(e)}"
        )


@router.get("/stats", response_model=StatsResponse)
async def get_stats():
    """
    Get sandbox manager statistics.
    
    Returns overall stats about:
    - Total sessions
    - Total sandboxes
    - Activity metrics
    - Cleanup task status
    """
    stats = sandbox_manager.get_stats()
    return StatsResponse(**stats)


@router.post("/cleanup/start")
async def start_cleanup():
    """
    Start background cleanup task.
    
    The cleanup task will:
    - Stop idle sandboxes (> SANDBOX_IDLE_TIMEOUT)
    """
    try:
        sandbox_manager.start_cleanup_task()
        return {"status": "success", "message": "Cleanup task started"}
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to start cleanup: {str(e)}"
        )


@router.post("/cleanup/stop")
async def stop_cleanup():
    """Stop background cleanup task"""
    try:
        await sandbox_manager.stop_cleanup_task()
        return {"status": "success", "message": "Cleanup task stopped"}
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to stop cleanup: {str(e)}"
        )


@router.post("/sessions/{session_id}/sync")
async def sync_from_docker(session_id: str):
    """
    Sync sandboxes from Docker to local cache.
    
    Useful when:
    - Accessing sandboxes created by another process (FastAPI → Celery or vice versa)
    - Recovering from process restart
    - Ensuring local cache is up-to-date with Docker containers
    
    Returns:
        Number of sandboxes reconnected
    """
    try:
        reconnected = await sandbox_manager.sync_from_docker(session_id)
        return {
            "status": "success",
            "session_id": session_id,
            "reconnected": reconnected,
            "message": f"Synced {reconnected} sandboxes from Docker"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Sync failed: {str(e)}"
        )
