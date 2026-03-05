"""
🎬 完整视频生成流水线
一键执行：生成静态图 → 添加动画 → 注册组件 → 组装完整视频

包含所有场景类型：
- Chart场景（bar/line/scatter/pie charts）
- Opening场景（开场）
- Closing场景（结尾）
- Stat Cards场景（数据卡片）

🚀 并行优化：
- 图表场景和其他场景的静态图生成并行执行
- 图表场景和其他场景的动画添加并行执行
- 并行时每个任务使用 --workers 指定的线程数

使用方法：
    python "infographic_generation/pipeline_full_video.py" --config generated_xxx.json
    
可选参数：
    --workers 5          # 每个任务的并行线程数（默认5，并行时总并发约 workers*2）
    --skip-static       # 跳过静态图生成（如果已生成）
    --skip-animation    # 跳过动画生成（如果已生成）
    --skip-other-scenes # 跳过其他场景生成（opening/closing/stat_cards）
    --serial           # 使用串行模式（更稳定，但较慢）
"""

import subprocess
import argparse
import time
import json
import os
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed


def run_command(cmd, description):
    """运行命令并显示进度"""
    print(f"\n{'='*70}")
    print(f"🚀 {description}")
    print(f"{'='*70}")
    
    start_time = time.time()
    result = subprocess.run(cmd, shell=True, capture_output=False)
    elapsed = time.time() - start_time
    
    if result.returncode == 0:
        print(f"✅ {description} 完成！耗时: {elapsed:.1f}秒")
        return True
    else:
        print(f"❌ {description} 失败！")
        return False


def run_command_parallel(cmd, description, prefix="", capture_output=False):
    """运行命令（用于并行执行，不打印分隔线）"""
    start_time = time.time()
    
    # 如果有前缀，在命令中添加前缀处理（通过环境变量传递）
    if prefix:
        # 使用环境变量传递前缀，子进程可以通过读取环境变量来添加前缀
        env = os.environ.copy()
        env['OUTPUT_PREFIX'] = prefix
        # 注意：子进程需要自己处理前缀，这里只是传递
        result = subprocess.run(cmd, shell=True, capture_output=capture_output, env=env)
    else:
        result = subprocess.run(cmd, shell=True, capture_output=capture_output)
    
    elapsed = time.time() - start_time  # ✅ 正确缩进
    
    if result.returncode == 0:
        if not capture_output:
            print(f"✅ {description} 完成！耗时: {elapsed:.1f}秒")
        return (True, description, elapsed)
    else:
        if not capture_output:
            print(f"❌ {description} 失败！耗时: {elapsed:.1f}秒")
        return (False, description, elapsed)


def extract_task_id_from_config(config_path):
    """从配置文件名提取 task_id"""
    import re
    filename = Path(config_path).name
    # 匹配 generated_<task_id>_aligned.json 或 generated_<task_id>.json
    match = re.search(r'generated_(\d{8}_\d{6})', filename)
    if match:
        return match.group(1)
    else:
        # 如果没有匹配到，使用当前时间戳
        from datetime import datetime
        return datetime.now().strftime('%Y%m%d_%H%M%S')


def count_scenes_from_config(config_path):
    """从配置文件统计场景数量"""
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        scenes = config.get('scenes', [])
        
        chart_count = len([s for s in scenes if s.get('type') == 'chart'])
        opening_count = len([s for s in scenes if s.get('type') == 'opening'])
        closing_count = len([s for s in scenes if s.get('type') == 'closing'])
        stat_cards_count = len([s for s in scenes if s.get('type') == 'stat_cards'])
        other_count = opening_count + closing_count + stat_cards_count
        
        return {
            'chart': chart_count,
            'opening': opening_count,
            'closing': closing_count,
            'stat_cards': stat_cards_count,
            'other': other_count,
            'total': len(scenes)
        }
    except Exception as e:
        print(f"⚠️  无法读取配置文件统计场景数量: {e}")
        return None


def main():
    runtime_base = os.environ.get("VIDEO_RUNTIME_BASE", "/workspace/video_runtime")
    default_components_output = os.environ.get(
        "VIDEO_COMPONENTS_OUTPUT_BASE",
        f"{runtime_base}/claude_tsx_components",
    )
    default_animated_output = os.environ.get(
        "VIDEO_ANIMATED_OUTPUT_BASE",
        f"{runtime_base}/claude_tsx_animated",
    )

    parser = argparse.ArgumentParser(description='完整视频生成流水线（包含所有场景类型）')
    parser.add_argument('--config', required=True, help='JSON配置文件路径')
    parser.add_argument('--workers', type=int, default=5, help='每个任务的并行线程数（默认5）')
    parser.add_argument('--skip-static', action='store_true', help='跳过静态图生成')
    parser.add_argument('--skip-animation', action='store_true', help='跳过动画生成')
    parser.add_argument('--skip-other-scenes', action='store_true', help='跳过其他场景生成（opening/closing/stat_cards）')
    parser.add_argument('--serial', action='store_true', help='使用串行模式（更稳定，但较慢）')
    parser.add_argument(
        '--components-output-base',
        type=str,
        default=default_components_output,
        help='静态组件输出基础目录（任务会写入子目录）',
    )
    parser.add_argument(
        '--animated-output-base',
        type=str,
        default=default_animated_output,
        help='动画组件输出基础目录（任务会写入子目录）',
    )
    parser.add_argument('--skip-copy', action='store_true', help='跳过 Step 3/5 复制组件文件')
    parser.add_argument('--skip-compose', action='store_true', help='跳过 Step 4/5 组装完整视频')
    
    args = parser.parse_args()
    
    config_path = Path(args.config)
    if not config_path.exists():
        print(f"❌ 配置文件不存在: {config_path}")
        return
    
    # 提取 task_id 用于组件隔离
    task_id = extract_task_id_from_config(config_path)
    
    print("🎬"*30)
    print("🎥 完整视频生成流水线")
    print("🎬"*30)
    print(f"\n📊 配置文件: {config_path}")
    print(f"🆔 任务ID: {task_id}")
    print(f"📁 静态输出目录: {args.components_output_base}")
    print(f"📁 动画输出目录: {args.animated_output_base}")
    
    # 每个任务使用的线程数（简单直接：直接用 workers）
    workers_per_task = args.workers
    
    if args.serial:
        mode_str = "串行模式"
        total_concurrent = workers_per_task
    else:
        # 并行模式：两个任务同时运行
        total_concurrent = workers_per_task * 2 if not args.skip_other_scenes else workers_per_task
        mode_str = f"并行模式（总并发约 {total_concurrent}）"
    
    print(f"⚡ 模式: {mode_str}")
    print(f"⚡ 每个任务线程数: {workers_per_task}")
    
    total_start = time.time()
    script_dir = Path(__file__).parent
    
    # 预先统计场景数量（用于显示）
    scene_counts = count_scenes_from_config(args.config)
    
    # ========== Step 1: 生成静态图（图表场景 + 其他场景）==========
    if not args.skip_static:
        print(f"\n{'='*70}")
        if args.serial:
            print(f"📦 Step 1/5: 串行生成静态TSX组件")
        else:
            print(f"📦 Step 1/5: 并行生成静态TSX组件")
        print(f"{'='*70}")
        
        # 显示场景统计
        if scene_counts:
            print(f"\n📊 场景统计:")
            print(f"   📈 图表场景: {scene_counts['chart']} 个")
            if not args.skip_other_scenes:
                print(f"   🎬 Opening: {scene_counts['opening']} 个")
                print(f"   🎉 Closing: {scene_counts['closing']} 个")
                print(f"   📊 Stat Cards: {scene_counts['stat_cards']} 个")
                print(f"   📦 其他场景总计: {scene_counts['other']} 个")
            print(f"   📋 总场景数: {scene_counts['total']} 个")
        
        tasks = []
        
        # 任务1: 生成图表场景静态图
        chart_script = script_dir / "generate_with_claude.py"
        chart_cmd = (
            f'python "{chart_script}" --config "{args.config}" --workers {workers_per_task} '
            f'--output "{args.components_output_base}" --task-id {task_id}'
        )
        chart_desc = f"生成图表场景静态TSX组件 ({scene_counts['chart'] if scene_counts else '?'} 个场景)"
        tasks.append((chart_cmd, chart_desc, "[图表]"))
        
        # 任务2: 生成其他场景静态图（如果未跳过）
        if not args.skip_other_scenes:
            other_script = script_dir / "generate_other_scenes.py"
            other_cmd = (
                f'python "{other_script}" --config "{args.config}" --workers {workers_per_task} '
                f'--output "{args.components_output_base}" --task-id {task_id}'
            )
            other_desc = f"生成其他场景静态TSX组件 ({scene_counts['other'] if scene_counts else '?'} 个场景)"
            tasks.append((other_cmd, other_desc, "[其他]"))
        
        # 显示任务概览
        if len(tasks) > 1 and not args.serial:
            print(f"\n🚀 并行任务概览:")
            for i, (_, desc, prefix) in enumerate(tasks, 1):
                print(f"   任务 {i}: {desc} (前缀: {prefix})")
            print(f"   每个任务使用 {workers_per_task} 个线程")
            print(f"   总并发数: {len(tasks) * workers_per_task}")
            print(f"\n💡 提示: 两个任务的输出会实时显示，可能交错出现\n")
        
        # 执行任务
        if len(tasks) == 1 or args.serial:
            # 只有一个任务或串行模式，顺序执行
            for cmd, desc, prefix in tasks:
                print(f"\n🚀 开始: {desc}")
                success, desc, elapsed = run_command_parallel(cmd, desc, prefix="", capture_output=False)
                if not success and "图表场景" in desc:
                    print("\n❌ 流水线中断！")
                    return
                elif not success:
                    print("\n⚠️  其他场景生成失败，但继续执行...")
        else:
            # 多个任务，并行执行（实时显示输出）
            print(f"🚀 开始并行执行 {len(tasks)} 个任务...\n")
            with ThreadPoolExecutor(max_workers=len(tasks)) as executor:
                futures = {executor.submit(run_command_parallel, cmd, desc, prefix, capture_output=False): (cmd, desc, prefix) 
                          for cmd, desc, prefix in tasks}
                
                results = []
                for future in as_completed(futures):
                    result = future.result()
                    results.append(result)
                
                # 检查结果
                chart_success = any(r[0] and "图表场景" in r[1] for r in results)
                other_success = any(r[0] and "其他场景" in r[1] for r in results) if not args.skip_other_scenes else True
                
                if not chart_success:
                    print("\n❌ 图表场景生成失败，流水线中断！")
                    return
                if not other_success:
                    print("\n⚠️  其他场景生成失败，但继续执行...")
    else:
        print(f"\n⏭️  跳过 Step 1/5: 生成静态TSX组件")
    
    # ========== Step 2: 添加动画（图表场景 + 其他场景）==========
    if not args.skip_animation:
        print(f"\n{'='*70}")
        if args.serial:
            print(f"🎬 Step 2/5: 串行添加动画")
        else:
            print(f"🎬 Step 2/5: 并行添加动画")
        print(f"{'='*70}")
        
        # 显示场景统计
        if scene_counts:
            print(f"\n📊 场景统计:")
            print(f"   📈 图表场景: {scene_counts['chart']} 个")
            if not args.skip_other_scenes:
                print(f"   📦 其他场景: {scene_counts['other']} 个")
        
        tasks = []
        
        # 任务1: 为图表场景添加动画
        chart_anim_script = script_dir / "add_animations_to_static.py"
        chart_anim_cmd = (
            f'python "{chart_anim_script}" --config "{args.config}" --workers {workers_per_task} '
            f'--input "{args.components_output_base}" --output "{args.animated_output_base}" --task-id {task_id}'
        )
        chart_anim_desc = f"为图表场景添加动画 ({scene_counts['chart'] if scene_counts else '?'} 个场景)"
        tasks.append((chart_anim_cmd, chart_anim_desc, "[图表]"))
        
        # 任务2: 为其他场景添加动画（如果未跳过）
        if not args.skip_other_scenes:
            other_anim_script = script_dir / "add_animations_to_other_scenes.py"
            other_anim_cmd = (
                f'python "{other_anim_script}" --config "{args.config}" --workers {workers_per_task} '
                f'--static-dir "{args.components_output_base}" --animated-dir "{args.animated_output_base}" --task-id {task_id}'
            )
            other_anim_desc = f"为其他场景添加动画 ({scene_counts['other'] if scene_counts else '?'} 个场景)"
            tasks.append((other_anim_cmd, other_anim_desc, "[其他]"))
        
        # 显示任务概览
        if len(tasks) > 1 and not args.serial:
            print(f"\n🚀 并行任务概览:")
            for i, (_, desc, prefix) in enumerate(tasks, 1):
                print(f"   任务 {i}: {desc} (前缀: {prefix})")
            print(f"   每个任务使用 {workers_per_task} 个线程")
            print(f"   总并发数: {len(tasks) * workers_per_task}")
            print(f"\n💡 提示: 两个任务的输出会实时显示，可能交错出现\n")
        
        # 执行任务
        if len(tasks) == 1 or args.serial:
            # 只有一个任务或串行模式，顺序执行
            for cmd, desc, prefix in tasks:
                print(f"\n🚀 开始: {desc}")
                success, desc, elapsed = run_command_parallel(cmd, desc, prefix="", capture_output=False)
                if not success and "图表场景" in desc:
                    print("\n❌ 流水线中断！")
                    return
                elif not success:
                    print("\n⚠️  其他场景动画添加失败，但继续执行...")
        else:
            # 多个任务，并行执行（实时显示输出）
            print(f"🚀 开始并行执行 {len(tasks)} 个任务...\n")
            with ThreadPoolExecutor(max_workers=len(tasks)) as executor:
                futures = {executor.submit(run_command_parallel, cmd, desc, prefix, capture_output=False): (cmd, desc, prefix) 
                          for cmd, desc, prefix in tasks}
                
                results = []
                for future in as_completed(futures):
                    result = future.result()
                    results.append(result)
                
                # 检查结果
                chart_success = any(r[0] and "图表场景" in r[1] for r in results)
                other_success = any(r[0] and "其他场景" in r[1] for r in results) if not args.skip_other_scenes else True
                
                if not chart_success:
                    print("\n❌ 图表场景动画添加失败，流水线中断！")
                    return
                if not other_success:
                    print("\n⚠️  其他场景动画添加失败，但继续执行...")
    else:
        print(f"\n⏭️  跳过 Step 2/5: 添加动画")
    
    # ========== Step 3: 复制组件文件（但不注册为独立Composition）==========
    if args.skip_copy:
        print("\n⏭️  跳过 Step 3/5: 复制组件文件")
    else:
        register_script = script_dir / "auto_register_components.py"
        register_cmd = (
            f'python "{register_script}" --animated --task-id {task_id} --copy-only '
            f'--base-output-dir "{args.animated_output_base}"'
        )
        if not run_command(register_cmd, "Step 3/5: 复制组件文件"):
            print("\n⚠️  组件复制失败，但继续执行...")
    
    # ========== Step 4: 组装完整视频 ==========
    if args.skip_compose:
        print("\n⏭️  跳过 Step 4/5: 组装完整视频")
    else:
        # 注意：在 Docker 环境中，Remotion 项目可能不存在，这一步可能会失败
        # 但这是正常的，TSX 组件文件已经生成，可以在 Remotion 项目中手动注册
        compose_script = script_dir / "auto_compose_video.py"
        compose_cmd = f'python "{compose_script}" --config "{args.config}" --task-id {task_id}'
        if not run_command(compose_cmd, "Step 4/5: 组装完整视频"):
            print("\n⚠️  组装完整视频失败（这在 Docker 环境中是正常的）")
            print("   TSX 组件文件已生成，可以在 Remotion 项目中手动注册")
            # 不中断流水线，继续执行
    
    # 完成！
    total_elapsed = time.time() - total_start
    
    print(f"\n{'='*70}")
    print(f"🎉 流水线执行完成！")
    print(f"{'='*70}")
    print(f"⏱️  总耗时: {total_elapsed:.1f}秒 ({total_elapsed/60:.1f}分钟)")
    print(f"\n💡 下一步：")
    print(f"   1. 在 Remotion Studio 中查看完整视频")
    print(f"   2. 可以预览单个场景：")
    print(f"      - 图表场景: SceneChart1, SceneChart2, ...")
    print(f"      - Opening: SceneOpening1Component")
    print(f"      - Closing: SceneClosing1Component")
    print(f"      - Stat Cards: SceneStatsComponent（如果有）")
    print(f"   3. 或者预览完整串联视频（以 'FullVideo' 结尾的Composition）")
    print(f"\n🚀 如果 Remotion Studio 未运行，执行: npm start")


if __name__ == '__main__':
    main()
