"""工作空间管理器

管理 DeepEye 的本地文件存储，包括图片、数据、缓存等。
未来将被 storage 层替代，但保持接口兼容。
"""

from pathlib import Path
from typing import Optional, List
import os
import shutil
import uuid
import time
from datetime import datetime, timedelta


class WorkspaceManager:
    """工作空间管理器
    
    管理 DeepEye 的本地文件存储，包括图片、数据、缓存等。
    支持自动清理过期文件。
    
    Example:
        >>> workspace = WorkspaceManager()
        >>> plot_dir = workspace.get_plot_dir("exec-123")
        >>> # 使用 plot_dir 保存图片
        >>> workspace.cleanup_old_plots(days=7)  # 清理 7 天前的图片
    """
    
    def __init__(
        self, 
        base_path: Optional[str] = None,
        auto_cleanup_days: int = 7
    ):
        """初始化工作空间
        
        Args:
            base_path: 工作空间根目录，默认为 ~/.deepeye/workspace
            auto_cleanup_days: 自动清理文件的天数，默认 7 天
        """
        if base_path is None:
            base_path = os.path.expanduser("~/.deepeye/workspace")
        
        self.base_path = Path(base_path)
        self.auto_cleanup_days = auto_cleanup_days
        self._ensure_directories()
    
    def _ensure_directories(self):
        """确保必要的目录存在"""
        dirs = ["plots", "data", "cache", "temp", "logs"]
        for dir_name in dirs:
            (self.base_path / dir_name).mkdir(parents=True, exist_ok=True)
    
    def get_plot_dir(self, execution_id: Optional[str] = None) -> Path:
        """获取图片目录
        
        Args:
            execution_id: 执行 ID，用于隔离不同执行的文件。
                         如果为 None，自动生成一个新的 UUID
        
        Returns:
            图片目录路径
            
        Example:
            >>> workspace = WorkspaceManager()
            >>> plot_dir = workspace.get_plot_dir("exec-123")
            >>> print(plot_dir)
            ~/.deepeye/workspace/plots/exec-123
        """
        if execution_id is None:
            execution_id = str(uuid.uuid4())
        
        plot_dir = self.base_path / "plots" / execution_id
        plot_dir.mkdir(parents=True, exist_ok=True)
        return plot_dir
    
    def cleanup_plot_dir(self, execution_id: str):
        """清理指定执行 ID 的图片目录
        
        Args:
            execution_id: 执行 ID
            
        Example:
            >>> workspace = WorkspaceManager()
            >>> workspace.cleanup_plot_dir("exec-123")
        """
        plot_dir = self.base_path / "plots" / execution_id
        if plot_dir.exists():
            shutil.rmtree(plot_dir)
    
    def cleanup_old_plots(self, days: Optional[int] = None) -> int:
        """清理过期的图片目录
        
        Args:
            days: 清理多少天之前的文件，默认使用 auto_cleanup_days
        
        Returns:
            清理的目录数量
            
        Example:
            >>> workspace = WorkspaceManager()
            >>> count = workspace.cleanup_old_plots(days=7)
            >>> print(f"清理了 {count} 个过期目录")
        """
        if days is None:
            days = self.auto_cleanup_days
        
        plots_dir = self.base_path / "plots"
        if not plots_dir.exists():
            return 0
        
        cutoff_time = time.time() - (days * 24 * 60 * 60)
        cleaned_count = 0
        
        for execution_dir in plots_dir.iterdir():
            if execution_dir.is_dir():
                # 检查目录的修改时间
                if execution_dir.stat().st_mtime < cutoff_time:
                    shutil.rmtree(execution_dir)
                    cleaned_count += 1
        
        return cleaned_count
    
    def list_plot_executions(self) -> List[dict]:
        """列出所有图片执行记录
        
        Returns:
            执行记录列表，每个记录包含：
                - execution_id: 执行 ID
                - created_at: 创建时间
                - file_count: 文件数量
                - total_size: 总大小（字节）
                
        Example:
            >>> workspace = WorkspaceManager()
            >>> executions = workspace.list_plot_executions()
            >>> for exec in executions:
            ...     print(f"{exec['execution_id']}: {exec['file_count']} files")
        """
        plots_dir = self.base_path / "plots"
        if not plots_dir.exists():
            return []
        
        executions = []
        for execution_dir in plots_dir.iterdir():
            if execution_dir.is_dir():
                files = list(execution_dir.glob("*"))
                total_size = sum(f.stat().st_size for f in files if f.is_file())
                
                executions.append({
                    "execution_id": execution_dir.name,
                    "created_at": datetime.fromtimestamp(execution_dir.stat().st_mtime),
                    "file_count": len(files),
                    "total_size": total_size
                })
        
        # 按创建时间降序排序
        executions.sort(key=lambda x: x["created_at"], reverse=True)
        return executions
    
    def get_data_dir(self) -> Path:
        """获取数据目录
        
        Returns:
            数据目录路径
        """
        return self.base_path / "data"
    
    def get_cache_dir(self) -> Path:
        """获取缓存目录
        
        Returns:
            缓存目录路径
        """
        return self.base_path / "cache"
    
    def get_temp_dir(self) -> Path:
        """获取临时目录
        
        Returns:
            临时目录路径
        """
        return self.base_path / "temp"
    
    def get_logs_dir(self) -> Path:
        """获取日志目录
        
        Returns:
            日志目录路径
        """
        return self.base_path / "logs"
    
    def cleanup_temp(self):
        """清理临时目录
        
        删除临时目录中的所有文件，但保留目录本身。
        """
        temp_dir = self.get_temp_dir()
        if temp_dir.exists():
            shutil.rmtree(temp_dir)
            temp_dir.mkdir(parents=True, exist_ok=True)
    
    def get_workspace_info(self) -> dict:
        """获取工作空间信息
        
        Returns:
            工作空间信息字典，包含：
                - base_path: 根目录路径
                - plots_count: 图片执行数量
                - total_size: 总大小（字节）
                - auto_cleanup_days: 自动清理天数
                
        Example:
            >>> workspace = WorkspaceManager()
            >>> info = workspace.get_workspace_info()
            >>> print(f"工作空间大小: {info['total_size'] / 1024 / 1024:.2f} MB")
        """
        total_size = 0
        for root, dirs, files in os.walk(self.base_path):
            for file in files:
                file_path = Path(root) / file
                if file_path.is_file():
                    total_size += file_path.stat().st_size
        
        plots_dir = self.base_path / "plots"
        plots_count = len(list(plots_dir.iterdir())) if plots_dir.exists() else 0
        
        return {
            "base_path": str(self.base_path),
            "plots_count": plots_count,
            "total_size": total_size,
            "auto_cleanup_days": self.auto_cleanup_days
        }


# 全局单例
_workspace_manager: Optional[WorkspaceManager] = None


def get_workspace_manager(
    base_path: Optional[str] = None,
    auto_cleanup_days: int = 7
) -> WorkspaceManager:
    """获取全局工作空间管理器
    
    Args:
        base_path: 工作空间根目录，默认为 ~/.deepeye/workspace
        auto_cleanup_days: 自动清理文件的天数，默认 7 天
    
    Returns:
        WorkspaceManager 实例
        
    Example:
        >>> workspace = get_workspace_manager()
        >>> plot_dir = workspace.get_plot_dir()
    """
    global _workspace_manager
    if _workspace_manager is None:
        _workspace_manager = WorkspaceManager(
            base_path=base_path,
            auto_cleanup_days=auto_cleanup_days
        )
    return _workspace_manager


def reset_workspace_manager():
    """重置全局工作空间管理器（主要用于测试）"""
    global _workspace_manager
    _workspace_manager = None

