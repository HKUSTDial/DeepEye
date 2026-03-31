"""
自动组装完整视频
读取JSON配置，自动在Root.tsx中注册VideoComposer完整视频

使用方法：
    python "infographic generation/auto_compose_video.py" --config generated_xxx.json
"""

import json
import os
import re
import argparse
from pathlib import Path

from app.node.video.render.component_registry import update_video_composer_with_mapping
from app.node.video.render.frontend_sync import copy_components_to_frontend
from app.node.video.render.root_registration import add_video_composer_to_root

VIDEO_RUNTIME_BASE = Path(os.getenv("VIDEO_RUNTIME_BASE", "/workspace/video_runtime"))
DEFAULT_ANIMATED_OUTPUT_DIR = Path(
    os.getenv("VIDEO_ANIMATED_OUTPUT_BASE", str(VIDEO_RUNTIME_BASE / "claude_tsx_animated"))
)


def calculate_total_duration(config_data):
    """从JSON配置计算视频总时长（帧数）"""
    fps = config_data['meta']['fps']
    
    # 找到所有渲染场景（opening, chart, stat_cards, closing）
    all_scenes = [s for s in config_data['scenes'] 
                  if s['type'] in ['opening', 'chart', 'stat_cards', 'closing']]
    
    if not all_scenes:
        raise ValueError("配置文件中没有找到任何可渲染的场景")
    
    # 获取最后一个场景的结束时间（支持回退方案）
    last_scene = all_scenes[-1]
    
    # 尝试从 time_range 获取结束时间
    if 'time_range' in last_scene and isinstance(last_scene['time_range'], list) and len(last_scene['time_range']) >= 2:
        end_time = last_scene['time_range'][1]
    else:
        # 回退方案：从 narration 计算，或使用估算值
        if last_scene.get('narration') and isinstance(last_scene['narration'], list) and len(last_scene['narration']) > 0:
            last_narr = last_scene['narration'][-1]
            if 'time_end' in last_narr and isinstance(last_narr['time_end'], (int, float)):
                end_time = last_narr['time_end']
            else:
                # 估算：每个 narration 约 3 秒，每个场景至少 5 秒
                estimated_duration = len(last_scene['narration']) * 3.0
                # 计算前面所有场景的时间
                previous_time = sum(
                    max(5.0, len(s.get('narration', [])) * 3.0) 
                    for s in all_scenes[:-1]
                )
                end_time = previous_time + max(5.0, estimated_duration)
        else:
            # 完全没有时间信息，使用默认值
            end_time = len(all_scenes) * 5.0  # 每个场景默认 5 秒
    
    # 转换为帧数
    total_frames = round(end_time * fps)
    
    # 统计各类型场景数量
    scene_counts = {
        'opening': len([s for s in all_scenes if s['type'] == 'opening']),
        'chart': len([s for s in all_scenes if s['type'] == 'chart']),
        'stat_cards': len([s for s in all_scenes if s['type'] == 'stat_cards']),
        'closing': len([s for s in all_scenes if s['type'] == 'closing']),
    }
    
    return total_frames, scene_counts


def get_video_id_from_config(config_data):
    """从配置文件内容生成视频ID（基于meta.title）"""
    title = config_data.get('meta', {}).get('title', '')
    
    if title:
        # 从标题生成ID：移除特殊字符，将下划线替换为空格，转换为PascalCase
        # 例如: "Google Play Store Analysis" -> "GooglePlayStoreAnalysis"
        # 例如: "Exploring ART_AND_DESIGN Apps" -> "ExploringArtAndDesignApps"
        # Remotion要求：只能包含 a-z, A-Z, 0-9, CJK字符和连字符 -
        title_clean = title.replace('_', ' ')  # 先将下划线替换为空格
        title_clean = re.sub(r'[^\w\s]', '', title_clean)  # 移除其他特殊字符
        parts = title_clean.split()
        video_id = ''.join(word.capitalize() for word in parts if word)
        return video_id + 'FullVideo'
    else:
        # 如果没有title，回退到文件名方式
        return 'GeneratedFullVideo'


def get_component_prefix_from_config(config_data):
    """
    从配置文件内容生成组件前缀（基于meta.title）
    使用与 extract_dataset_name 相同的逻辑，确保命名一致
    """
    title = config_data.get('meta', {}).get('title', '')
    
    if title:
        # 使用与 extract_dataset_name 完全相同的逻辑
        # 去掉空格和特殊字符，只保留字母数字
        dataset_name = ''.join(c for c in title if c.isalnum())
        # 如果太长，截取前20个字符（与 extract_dataset_name 保持一致）
        if len(dataset_name) > 20:
            dataset_name = dataset_name[:20]
        return dataset_name
    else:
        return None


def main():
    parser = argparse.ArgumentParser(description='自动组装完整视频到Root.tsx')
    parser.add_argument('--config', required=True, help='JSON配置文件路径')
    parser.add_argument('--task-id', type=str, default=None, help='任务ID，用于生成简短的Composition ID')
    
    args = parser.parse_args()
    
    config_path = Path(args.config)
    
    if not config_path.exists():
        print(f"❌ 配置文件不存在: {config_path}")
        return
    
    print("="*70)
    print("🎬 自动组装完整视频")
    print("="*70)
    
    # 读取配置
    with open(config_path, 'r', encoding='utf-8') as f:
        config_data = json.load(f)
    
    video_title = config_data['meta']['title']
    print(f"\n📊 视频标题: {video_title}")
    
    # 计算总时长
    total_frames, scene_counts = calculate_total_duration(config_data)
    fps = config_data['meta']['fps']
    duration_seconds = total_frames / fps
    
    total_scenes = sum(scene_counts.values())
    print(f"📊 场景数量: {total_scenes} (Opening: {scene_counts['opening']}, Chart: {scene_counts['chart']}, Stat Cards: {scene_counts['stat_cards']}, Closing: {scene_counts['closing']})")
    print(f"📊 总时长: {total_frames} 帧 ({duration_seconds:.1f} 秒 @ {fps}fps)")
    
    # 生成视频ID
    if args.task_id:
        # 使用简短的 task_id 格式，避免名字太长
        video_id = f"FullVideo-{args.task_id.replace('_', '-')}"
        print(f"📊 视频ID: {video_id} (基于任务ID)")
    else:
        # 回退到基于标题的长ID
        video_id = get_video_id_from_config(config_data)
        print(f"📊 视频ID: {video_id} (基于标题)")
    
    # 生成组件前缀（保持基于标题，与组件文件名匹配）
    component_prefix = get_component_prefix_from_config(config_data)
    if component_prefix:
        print(f"📊 组件前缀: {component_prefix}")
    
    # 确定动画组件目录
    animated_components_dir = None
    if args.task_id:
        # 优先使用统一运行时目录（可由 VIDEO_ANIMATED_OUTPUT_BASE 覆盖）
        animated_components_dir = DEFAULT_ANIMATED_OUTPUT_DIR / args.task_id
    
    # 复制组件到前端目录（如果提供了 task_id 和 component_prefix）
    if component_prefix and args.task_id and animated_components_dir:
        print(f"\n📦 正在复制组件到前端目录...")
        try:
            copy_components_to_frontend(component_prefix, config_data, args.task_id, animated_components_dir)
        except Exception as e:
            print(f"⚠️  复制组件到前端失败: {e}")
            import traceback
            traceback.print_exc()
    
    # 更新前端 VideoComposer.tsx（如果提供了 component_prefix 和 task_id）
    # 注意：DeepEye-DataMagic 使用动态加载机制，不需要硬编码映射表
    # 组件会通过 API 获取并在浏览器中编译，所以跳过前端 VideoComposer 的自动更新
    if component_prefix and args.task_id:
        print(f"\n🔧 跳过前端 VideoComposer.tsx 自动更新（使用动态加载机制）...")
        print(f"   组件将通过 API 动态加载: /api/v1/video/components/{args.task_id}/")
        # update_frontend_video_composer(component_prefix, config_data, args.task_id)  # 已禁用
    
    # 自动更新后端 VideoComposer.tsx（如果提供了 component_prefix，用于 Remotion 项目）
    if component_prefix:
        print(f"\n🔧 正在更新后端 VideoComposer.tsx（Remotion 项目）...")
        video_composer_path = Path(__file__).parent.parent.parent / 'src' / 'components' / 'CustomInfographic' / 'VideoComposer.tsx'
        try:
            update_video_composer_with_mapping(component_prefix, config_data, video_composer_path, args.task_id)
        except Exception as e:
            print(f"⚠️  更新后端 VideoComposer 失败: {e}")
            import traceback
            traceback.print_exc()
    
    # 添加到Root.tsx
    print(f"\n🔧 正在注册到 Root.tsx...")
    
    try:
        success = add_video_composer_to_root(config_path, video_id, total_frames, scene_counts, component_prefix)
        
        if success:
            print(f"✅ 成功注册 VideoComposer: {video_id}")
            print(f"\n💡 现在你可以在 Remotion Studio 中预览完整视频！")
            print(f"   视频名称: {video_id}")
            print(f"   场景数量: {total_scenes}")
            print(f"   总时长: {duration_seconds:.1f}秒")
        
    except Exception as e:
        print(f"❌ 注册失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
