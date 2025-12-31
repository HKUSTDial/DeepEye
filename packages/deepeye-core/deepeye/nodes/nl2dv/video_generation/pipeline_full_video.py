"""
🎬 完整视频生成流水线
一键执行：生成静态图 → 添加动画 → 注册组件 → 组装完整视频

包含所有场景类型：
- Chart场景（bar/line/scatter/pie charts）
- Opening场景（开场）
- Closing场景（结尾）
- Stat Cards场景（数据卡片）

使用方法：
    python "infographic_generation/pipeline_full_video.py" --config generated_xxx.json
    
可选参数：
    --workers 5          # 并行线程数（默认5）
    --skip-static       # 跳过静态图生成（如果已生成）
    --skip-animation    # 跳过动画生成（如果已生成）
    --skip-other-scenes # 跳过其他场景生成（opening/closing/stat_cards）
"""

import subprocess
import argparse
import time
import sys
from pathlib import Path


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


def main():
    parser = argparse.ArgumentParser(description='完整视频生成流水线（包含所有场景类型）')
    parser.add_argument('--config', required=True, help='JSON配置文件路径')
    parser.add_argument('--workers', type=int, default=5, help='并行线程数')
    parser.add_argument('--skip-static', action='store_true', help='跳过静态图生成')
    parser.add_argument('--skip-animation', action='store_true', help='跳过动画生成')
    parser.add_argument('--skip-other-scenes', action='store_true', help='跳过其他场景生成（opening/closing/stat_cards）')
    
    args = parser.parse_args()
    
    config_path = Path(args.config)
    if not config_path.exists():
        print(f"❌ 配置文件不存在: {config_path}")
        return
    
    print("🎬"*30)
    print("🎥 完整视频生成流水线")
    print("🎬"*30)
    print(f"\n📊 配置文件: {config_path}")
    print(f"⚡ 并行线程数: {args.workers}")
    
    total_start = time.time()
    
    # Step 1: 生成图表场景静态图
    if not args.skip_static:
        script_dir = Path(__file__).parent
        script_path = script_dir / "generate_with_claude.py"
        cmd = f'python "{script_path}" --config "{args.config}" --workers {args.workers}'
        if not run_command(cmd, "Step 1/6: 生成图表场景静态TSX组件"):
            print("\n❌ 流水线中断！")
            return
    else:
        print(f"\n⏭️  跳过 Step 1/6: 生成图表场景静态TSX组件")
    
    # Step 1.5: 生成其他场景静态图（Opening/Closing/Stat Cards）
    if not args.skip_static and not args.skip_other_scenes:
        script_dir = Path(__file__).parent
        script_path = script_dir / "generate_other_scenes.py"
        cmd = f'python "{script_path}" --config "{args.config}" --workers {args.workers}'
        if not run_command(cmd, "Step 2/6: 生成其他场景静态TSX组件（Opening/Closing/Stat Cards）"):
            print("\n⚠️  其他场景生成失败，但继续执行...")
    else:
        if args.skip_static:
            print(f"\n⏭️  跳过 Step 2/6: 生成其他场景静态TSX组件")
        elif args.skip_other_scenes:
            print(f"\n⏭️  跳过 Step 2/6: 生成其他场景静态TSX组件（--skip-other-scenes）")
    
    # Step 2: 为图表场景添加动画
    if not args.skip_animation:
        script_dir = Path(__file__).parent
        script_path = script_dir / "add_animations_to_static.py"
        cmd = f'python "{script_path}" --config "{args.config}" --workers {args.workers}'
        if not run_command(cmd, "Step 3/6: 为图表场景添加动画"):
            print("\n❌ 流水线中断！")
            return
    else:
        print(f"\n⏭️  跳过 Step 3/6: 为图表场景添加动画")
    
    # Step 2.5: 为其他场景添加动画
    if not args.skip_animation and not args.skip_other_scenes:
        script_dir = Path(__file__).parent
        script_path = script_dir / "add_animations_to_other_scenes.py"
        cmd = f'python "{script_path}" --config "{args.config}" --workers {args.workers}'
        if not run_command(cmd, "Step 4/6: 为其他场景添加动画（Opening/Closing/Stat Cards）"):
            print("\n⚠️  其他场景动画添加失败，但继续执行...")
    else:
        if args.skip_animation:
            print(f"\n⏭️  跳过 Step 4/6: 为其他场景添加动画")
        elif args.skip_other_scenes:
            print(f"\n⏭️  跳过 Step 4/6: 为其他场景添加动画（--skip-other-scenes）")
    
    # Step 3: 注册单个场景组件
    script_dir = Path(__file__).parent
    script_path = script_dir / "auto_register_components.py"
    cmd = f'python "{script_path}" --animated'
    if not run_command(cmd, "Step 5/6: 注册所有场景组件到Root.tsx"):
        print("\n⚠️  组件注册失败，但继续执行...")
    
    # Step 4: 组装完整视频
    script_dir = Path(__file__).parent
    script_path = script_dir / "auto_compose_video.py"
    cmd = f'python "{script_path}" --config "{args.config}"'
    if not run_command(cmd, "Step 6/6: 组装完整视频"):
        print("\n❌ 流水线中断！")
        return
    
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


