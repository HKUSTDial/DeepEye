#!/usr/bin/env python3
"""
将之前生成的视频文件复制到 workspace 目录
这样用户可以在文件浏览器中查看这些文件
"""

import shutil
import os
from pathlib import Path
from typing import Optional

VIDEO_RUNTIME_BASE = Path(os.getenv("VIDEO_RUNTIME_BASE", "/workspace/video_runtime"))
DEFAULT_ANIMATED_OUTPUT_DIR = Path(
    os.getenv("VIDEO_ANIMATED_OUTPUT_BASE", str(VIDEO_RUNTIME_BASE / "claude_tsx_animated"))
)


def copy_video_to_workspace(
    task_id: str,
    backend_output_dir: Optional[Path] = None,
    workspace_base: Path = Path("/workspace")
) -> bool:
    """
    将指定 task_id 的视频文件复制到 workspace
    
    Args:
        task_id: 任务ID，例如 "<YYYYMMDD_HHMMSS>"
        backend_output_dir: 后端输出目录，如果为 None 则自动推断
        workspace_base: workspace 根目录，默认为 /workspace
        
    Returns:
        bool: 是否成功
    """
    # 自动推断后端输出目录
    if backend_output_dir is None:
        backend_output_dir = DEFAULT_ANIMATED_OUTPUT_DIR
    
    source_dir = backend_output_dir / task_id
    if not source_dir.exists():
        print(f"❌ 源目录不存在: {source_dir}")
        return False
    
    # 目标目录
    workspace_video_dir = workspace_base / "video_components" / task_id
    workspace_video_dir.mkdir(parents=True, exist_ok=True)
    
    # 复制 TSX 文件
    tsx_files = list(source_dir.glob("*.tsx"))
    if not tsx_files:
        print(f"⚠️  源目录中没有 TSX 文件: {source_dir}")
        return False
    
    copied_count = 0
    for src_file in tsx_files:
        dst_file = workspace_video_dir / src_file.name
        try:
            shutil.copy2(src_file, dst_file)
            copied_count += 1
            print(f"   ✅ {src_file.name} → {dst_file}")
        except Exception as e:
            print(f"   ❌ 复制失败 {src_file.name}: {e}")
    
    print(f"\n✅ 已复制 {copied_count}/{len(tsx_files)} 个文件到 workspace: {workspace_video_dir}")
    return copied_count > 0


def find_and_copy_config(task_id: str, workspace_base: Path = Path("/workspace")) -> bool:
    """
    查找并复制配置文件到 workspace
    
    Args:
        task_id: 任务ID
        workspace_base: workspace 根目录
        
    Returns:
        bool: 是否找到并复制了配置文件
    """
    # 查找配置文件（可能在多个位置）
    possible_config_paths = [
        workspace_base / "video_configs" / f"generated_{task_id}_aligned.json",
        Path("/workspace/video_configs") / f"generated_{task_id}_aligned.json",
    ]
    
    # 如果 workspace 中没有，尝试从后端代码目录查找
    script_dir = Path(__file__).parent
    backend_config_dir = script_dir.parent / "config"
    if backend_config_dir.exists():
        possible_config_paths.append(
            backend_config_dir / f"generated_{task_id}_aligned.json"
        )
    
    config_found = False
    for config_path in possible_config_paths:
        if config_path.exists():
            # 确保目标目录存在
            workspace_config_dir = workspace_base / "video_configs"
            workspace_config_dir.mkdir(parents=True, exist_ok=True)
            
            dst_config = workspace_config_dir / config_path.name
            try:
                shutil.copy2(config_path, dst_config)
                print(f"✅ 已复制配置文件: {dst_config}")
                config_found = True
                break
            except Exception as e:
                print(f"⚠️  复制配置文件失败: {e}")
    
    if not config_found:
        print(f"⚠️  未找到配置文件: generated_{task_id}_aligned.json")
    
    return config_found


def copy_all_previous_videos(
    workspace_base: Path = Path("/workspace"),
    task_ids: Optional[list[str]] = None
) -> None:
    """
    复制所有之前生成的视频文件到 workspace
    
    Args:
        workspace_base: workspace 根目录
        task_ids: 要复制的任务ID列表，如果为 None 则自动扫描所有任务
    """
    print("=" * 70)
    print("📦 复制之前的视频文件到 workspace")
    print("=" * 70)
    
    # 自动扫描所有任务
    if task_ids is None:
        backend_output_dir = DEFAULT_ANIMATED_OUTPUT_DIR
        
        if not backend_output_dir.exists():
            print(f"❌ 后端输出目录不存在: {backend_output_dir}")
            return
        
        # 扫描所有任务目录
        task_ids = []
        for item in backend_output_dir.iterdir():
            if item.is_dir() and item.name.startswith("202"):
                task_ids.append(item.name)
        
        task_ids.sort(reverse=True)  # 最新的在前
        print(f"\n📋 找到 {len(task_ids)} 个任务:")
        for tid in task_ids:
            print(f"   - {tid}")
    
    print(f"\n🚀 开始复制...\n")
    
    success_count = 0
    for task_id in task_ids:
        print(f"\n📦 处理任务: {task_id}")
        print("-" * 70)
        
        # 复制视频组件
        if copy_video_to_workspace(task_id, workspace_base=workspace_base):
            success_count += 1
        
        # 复制配置文件
        find_and_copy_config(task_id, workspace_base=workspace_base)
    
    print("\n" + "=" * 70)
    print(f"✅ 完成！成功复制 {success_count}/{len(task_ids)} 个任务")
    print("=" * 70)
    print(f"\n💡 现在你可以在文件浏览器中查看:")
    print(f"   - /workspace/video_configs/ - 配置文件")
    print(f"   - /workspace/video_components/ - 视频组件")


def main():
    """命令行入口"""
    import argparse
    
    parser = argparse.ArgumentParser(description='将之前生成的视频文件复制到 workspace')
    parser.add_argument('--task-id', type=str, default=None, help='要复制的任务ID（如果指定，只复制这一个）')
    parser.add_argument('--all', action='store_true', help='复制所有之前的任务')
    parser.add_argument('--workspace', type=str, default='/workspace', help='workspace 根目录')
    
    args = parser.parse_args()
    
    workspace_base = Path(args.workspace)
    
    if args.task_id:
        # 只复制指定的任务
        print(f"📦 复制任务: {args.task_id}")
        copy_video_to_workspace(args.task_id, workspace_base=workspace_base)
        find_and_copy_config(args.task_id, workspace_base=workspace_base)
    elif args.all:
        # 复制所有任务
        copy_all_previous_videos(workspace_base=workspace_base)
    else:
        # 默认复制最新的几个任务
        print("💡 提示: 使用 --all 复制所有任务，或使用 --task-id <id> 复制指定任务")
        print("\n📦 复制最新的 3 个任务...\n")
        backend_output_dir = DEFAULT_ANIMATED_OUTPUT_DIR
        
        if backend_output_dir.exists():
            task_ids = []
            for item in backend_output_dir.iterdir():
                if item.is_dir() and item.name.startswith("202"):
                    task_ids.append(item.name)
            task_ids.sort(reverse=True)
            
            # 只复制最新的 3 个
            copy_all_previous_videos(workspace_base=workspace_base, task_ids=task_ids[:3])
        else:
            print(f"❌ 后端输出目录不存在: {backend_output_dir}")


if __name__ == '__main__':
    main()
