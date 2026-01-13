"""Activity tracking for sandbox lifecycle management"""

from datetime import datetime, timedelta
from typing import Dict


class ActivityTracker:
    """
    Track sandbox activity for idle detection.
    
    Responsibilities:
    - Record last activity time for each session
    - Calculate idle time
    - Check if session should be stopped
    """
    
    def __init__(self):
        """Initialize activity tracker"""
        self._activities: Dict[str, datetime] = {}
    
    def record_activity(self, session_id: str) -> None:
        """
        Record activity for session.
        
        Args:
            session_id: Session ID
        """
        self._activities[session_id] = datetime.utcnow()
    
    def get_last_active(self, session_id: str) -> datetime | None:
        """
        Get last active time for session.
        
        Args:
            session_id: Session ID
            
        Returns:
            Last active datetime or None if never active
        """
        return self._activities.get(session_id)
    
    def get_idle_time(self, session_id: str) -> timedelta:
        """
        Get idle time for session.
        
        Args:
            session_id: Session ID
            
        Returns:
            Time since last activity, or timedelta.max if never active
        """
        last_active = self._activities.get(session_id)
        if not last_active:
            return timedelta.max
        return datetime.utcnow() - last_active
    
    def is_idle(self, session_id: str, timeout_seconds: int) -> bool:
        """
        Check if session is idle.
        
        Args:
            session_id: Session ID
            timeout_seconds: Idle timeout in seconds
            
        Returns:
            True if session has been idle longer than timeout
        """
        idle_time = self.get_idle_time(session_id)
        return idle_time.total_seconds() > timeout_seconds
    
    def should_stop(self, session_id: str, stop_timeout: int) -> bool:
        """
        Check if session should be stopped.
        
        Args:
            session_id: Session ID
            stop_timeout: Stop timeout in seconds
            
        Returns:
            True if session should be stopped
        """
        return self.is_idle(session_id, stop_timeout)
    
    def clear(self, session_id: str) -> None:
        """
        Clear activity record for session.
        
        Args:
            session_id: Session ID
        """
        self._activities.pop(session_id, None)
    
    def get_all_sessions(self) -> list[str]:
        """
        Get all tracked session IDs.
        
        Returns:
            List of session IDs
        """
        return list(self._activities.keys())
    
    def get_stats(self) -> dict:
        """
        Get activity statistics.
        
        Returns:
            Stats dict with session counts and average idle time
        """
        if not self._activities:
            return {
                "total_sessions": 0,
                "average_idle_seconds": 0
            }
        
        idle_times = [
            self.get_idle_time(sid).total_seconds() 
            for sid in self._activities.keys()
        ]
        
        return {
            "total_sessions": len(self._activities),
            "average_idle_seconds": sum(idle_times) / len(idle_times) if idle_times else 0
        }

