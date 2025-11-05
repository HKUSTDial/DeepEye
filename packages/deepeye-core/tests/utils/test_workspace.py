"""WorkspaceManager 测试"""

import pytest
import tempfile
import shutil
from pathlib import Path
import time

from deepeye.utils.workspace import WorkspaceManager, get_workspace_manager, reset_workspace_manager


@pytest.fixture
def temp_workspace():
    """创建临时工作空间"""
    temp_dir = tempfile.mkdtemp()
    workspace = WorkspaceManager(base_path=temp_dir, auto_cleanup_days=7)
    yield workspace
    # 清理
    if Path(temp_dir).exists():
        shutil.rmtree(temp_dir)


def test_workspace_initialization(temp_workspace):
    """测试工作空间初始化"""
    workspace = temp_workspace
    
    # 检查目录是否创建
    assert workspace.base_path.exists()
    assert (workspace.base_path / "plots").exists()
    assert (workspace.base_path / "data").exists()
    assert (workspace.base_path / "cache").exists()
    assert (workspace.base_path / "temp").exists()
    assert (workspace.base_path / "logs").exists()


def test_get_plot_dir(temp_workspace):
    """测试获取图片目录"""
    workspace = temp_workspace
    
    # 使用指定的 execution_id
    plot_dir = workspace.get_plot_dir("test-exec-123")
    assert plot_dir.exists()
    assert plot_dir.name == "test-exec-123"
    assert plot_dir.parent == workspace.base_path / "plots"
    
    # 使用自动生成的 execution_id
    plot_dir2 = workspace.get_plot_dir()
    assert plot_dir2.exists()
    assert plot_dir2 != plot_dir


def test_cleanup_plot_dir(temp_workspace):
    """测试清理图片目录"""
    workspace = temp_workspace
    
    # 创建图片目录
    plot_dir = workspace.get_plot_dir("test-exec-456")
    
    # 创建一些文件
    (plot_dir / "plot1.png").write_text("fake image data")
    (plot_dir / "plot2.png").write_text("fake image data")
    
    assert plot_dir.exists()
    assert len(list(plot_dir.iterdir())) == 2
    
    # 清理
    workspace.cleanup_plot_dir("test-exec-456")
    assert not plot_dir.exists()


def test_cleanup_old_plots(temp_workspace):
    """测试清理过期图片"""
    workspace = temp_workspace
    
    # 创建一些图片目录
    plot_dir1 = workspace.get_plot_dir("old-exec-1")
    plot_dir2 = workspace.get_plot_dir("old-exec-2")
    plot_dir3 = workspace.get_plot_dir("new-exec-3")
    
    # 修改前两个目录的修改时间（模拟旧文件）
    old_time = time.time() - (8 * 24 * 60 * 60)  # 8 天前
    plot_dir1.touch()
    plot_dir2.touch()
    import os
    os.utime(plot_dir1, (old_time, old_time))
    os.utime(plot_dir2, (old_time, old_time))
    
    # 清理 7 天前的文件
    cleaned_count = workspace.cleanup_old_plots(days=7)
    
    assert cleaned_count == 2
    assert not plot_dir1.exists()
    assert not plot_dir2.exists()
    assert plot_dir3.exists()


def test_list_plot_executions(temp_workspace):
    """测试列出图片执行记录"""
    workspace = temp_workspace
    
    # 创建一些图片目录和文件
    plot_dir1 = workspace.get_plot_dir("exec-1")
    (plot_dir1 / "plot1.png").write_bytes(b"fake image data 1" * 100)
    (plot_dir1 / "plot2.png").write_bytes(b"fake image data 2" * 100)
    
    plot_dir2 = workspace.get_plot_dir("exec-2")
    (plot_dir2 / "plot3.png").write_bytes(b"fake image data 3" * 100)
    
    # 列出执行记录
    executions = workspace.list_plot_executions()
    
    assert len(executions) == 2
    
    # 检查第一个执行记录
    exec1 = next(e for e in executions if e["execution_id"] == "exec-1")
    assert exec1["file_count"] == 2
    assert exec1["total_size"] > 0
    assert "created_at" in exec1
    
    exec2 = next(e for e in executions if e["execution_id"] == "exec-2")
    assert exec2["file_count"] == 1


def test_get_workspace_info(temp_workspace):
    """测试获取工作空间信息"""
    workspace = temp_workspace
    
    # 创建一些文件
    plot_dir = workspace.get_plot_dir("exec-info")
    (plot_dir / "plot.png").write_bytes(b"fake image data" * 1000)
    
    info = workspace.get_workspace_info()
    
    assert "base_path" in info
    assert "plots_count" in info
    assert "total_size" in info
    assert "auto_cleanup_days" in info
    
    assert info["plots_count"] == 1
    assert info["total_size"] > 0
    assert info["auto_cleanup_days"] == 7


def test_cleanup_temp(temp_workspace):
    """测试清理临时目录"""
    workspace = temp_workspace
    
    temp_dir = workspace.get_temp_dir()
    
    # 创建一些临时文件
    (temp_dir / "temp1.txt").write_text("temp data 1")
    (temp_dir / "temp2.txt").write_text("temp data 2")
    
    assert len(list(temp_dir.iterdir())) == 2
    
    # 清理
    workspace.cleanup_temp()
    
    assert temp_dir.exists()
    assert len(list(temp_dir.iterdir())) == 0


def test_global_workspace_manager():
    """测试全局工作空间管理器"""
    # 重置全局管理器
    reset_workspace_manager()
    
    # 获取全局管理器
    workspace1 = get_workspace_manager()
    workspace2 = get_workspace_manager()
    
    # 应该是同一个实例
    assert workspace1 is workspace2
    
    # 清理
    reset_workspace_manager()


def test_get_directory_methods(temp_workspace):
    """测试获取各种目录的方法"""
    workspace = temp_workspace
    
    data_dir = workspace.get_data_dir()
    assert data_dir.exists()
    assert data_dir.name == "data"
    
    cache_dir = workspace.get_cache_dir()
    assert cache_dir.exists()
    assert cache_dir.name == "cache"
    
    temp_dir = workspace.get_temp_dir()
    assert temp_dir.exists()
    assert temp_dir.name == "temp"
    
    logs_dir = workspace.get_logs_dir()
    assert logs_dir.exists()
    assert logs_dir.name == "logs"

