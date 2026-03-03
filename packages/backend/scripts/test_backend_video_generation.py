#!/usr/bin/env python3
"""
测试后端视频生成流程
用于验证：
1. 配置生成是否正常
2. TSX 组件生成是否正常
3. 文件是否保存到正确位置
"""

import sys
from pathlib import Path

# 必须在本项目的后端环境中运行（依赖 deepeye、app、langchain 等）
# 方式一（推荐）：在项目根目录用 uv 运行后端环境
#   uv run --package deepeye-backend python packages/backend/scripts/test_backend_video_generation.py
# 方式二：先进入 backend 再运行
#   cd packages/backend && uv run python scripts/test_backend_video_generation.py
def _find_repo_root(start: Path) -> Path:
    for candidate in (start, *start.parents):
        if (candidate / "packages" / "backend").exists() and (candidate / "packages" / "core").exists():
            return candidate
    raise RuntimeError(f"无法从脚本路径定位项目根目录: {start}")


project_root = _find_repo_root(Path(__file__).resolve())
backend_dir = project_root / "packages" / "backend"
core_dir = project_root / "packages" / "core"
sys.path.insert(0, str(backend_dir))
sys.path.insert(0, str(core_dir))

try:
    from deepeye.workflows.models import Node
    from app.node.video.node import VideoGeneratorHandler
except ModuleNotFoundError as e:
    print("❌ 导入失败：当前 Python 环境没有安装项目依赖。")
    print(f"   错误: {e}")
    print()
    print("请使用「后端环境」运行本脚本，任选一种方式：")
    print()
    print("  1) 在项目根目录执行（需已安装 uv）：")
    print("     uv run --package deepeye-backend python packages/backend/scripts/test_backend_video_generation.py")
    print()
    print("  2) 进入 backend 目录后执行：")
    print("     cd packages/backend")
    print("     uv run python scripts/test_backend_video_generation.py")
    print()
    sys.exit(1)


def test_backend_video_generation():
    """测试后端视频生成完整流程"""
    print("=" * 70)
    print("🧪 测试后端视频生成流程")
    print("=" * 70)
    print()
    
    # 准备测试数据：使用数值月份和标准日期格式，避免 LLM 规划成「时间解析」导致全 NaT 失败
    test_rows = [
        {"month": 1, "sales": 1200},
        {"month": 2, "sales": 1500},
        {"month": 3, "sales": 1800},
        {"month": 4, "sales": 2000},
    ]
    
    print("📊 测试数据:")
    print(f"  - 数据行数: {len(test_rows)}")
    print(f"  - 查询: 展示月度销售趋势（month=1,2,3,4）")
    print()
    
    # 创建 Node 对象
    test_node = Node(
        id="test_video_gen",
        type="video.generator",
        params={
            "language": "Chinese",  # 使用中文，方便测试
            "workers": 2  # 使用较少的 workers，加快测试速度
        }
    )
    
    # 准备输入
    inputs = {
        "rows": test_rows,
        "query": "展示月度销售趋势，生成包含动态图表的数据视频"
    }
    
    print("🔧 初始化 Handler...")
    try:
        handler = VideoGeneratorHandler(db=None, user_id="test_user")
        print("✅ Handler 初始化成功")
        print()
    except Exception as e:
        print(f"❌ Handler 初始化失败: {e}")
        return False
    
    # 执行节点
    print("🚀 开始执行视频生成流程...")
    print("   步骤 1: 生成视频配置（调用 LLM）")
    print("   步骤 2: 生成音频并对齐时间（调用 TTS API）")
    print("   步骤 3: 保存配置文件")
    print("   步骤 4: 生成 TSX 组件（调用 pipeline_full_video.py）")
    print("   预计耗时: 2-5 分钟")
    print()
    
    try:
        result = handler.execute(test_node, inputs, context=None)
        
        print()
        print("=" * 70)
        print("✅ 视频生成流程执行完成！")
        print("=" * 70)
        print()
        
        # 检查配置生成
        config = result.get("config", {})
        scenes = config.get("scenes", [])
        print(f"📋 配置生成: ✅ ({len(scenes)} 个场景)")
        
        # 检查配置文件
        config_path_str = result.get("config_path")
        if config_path_str:
            config_path = Path(config_path_str)
            print(f"💾 配置文件: {config_path}")
            if config_path.exists():
                config_size = config_path.stat().st_size
                print(f"   - 文件存在: ✅")
                print(f"   - 文件大小: {config_size / 1024:.1f} KB")
            else:
                print(f"   - 文件存在: ⚠️  (可能在其他位置)")
        
        # 检查音频生成
        has_audio_timing = False
        if scenes and scenes[0].get("narration"):
            first_narr = scenes[0]["narration"][0]
            if "time_start" in first_narr and "time_end" in first_narr:
                has_audio_timing = True
        
        print(f"🎵 音频生成: {'✅' if has_audio_timing else '⚠️  (可能未配置 Azure Speech API)'}")
        
        # 检查视频渲染（TSX 生成）
        video_info = result.get("video_info", {})
        video_status = video_info.get("status", "unknown")
        task_id = result.get("task_id") or video_info.get("task_id")
        
        print()
        print("=" * 70)
        print("🎬 TSX 组件生成状态")
        print("=" * 70)
        print(f"状态: {video_status}")
        print(f"Task ID: {task_id}")
        
        if video_status == "success":
            component_count = video_info.get("component_count", 0)
            video_path = result.get("video_path")
            workspace_dir = video_info.get("workspace_dir")
            
            print(f"✅ TSX 组件生成成功！")
            print(f"   - 组件数量: {component_count}")
            if video_path:
                print(f"   - 组件目录: {video_path}")
            if workspace_dir:
                workspace_path = Path(workspace_dir)
                if workspace_path.exists():
                    tsx_files = list(workspace_path.glob("*.tsx"))
                    print(f"   - Workspace 目录: {workspace_dir}")
                    print(f"   - TSX 文件数: {len(tsx_files)}")
                    if tsx_files:
                        print(f"   - 文件列表:")
                        for f in tsx_files[:5]:  # 只显示前5个
                            print(f"     • {f.name}")
                        if len(tsx_files) > 5:
                            print(f"     ... 还有 {len(tsx_files) - 5} 个文件")
            
            print()
            print("=" * 70)
            print("✅ 测试通过！后端可以正常生成 TSX 组件")
            print("=" * 70)
            print()
            print("📝 下一步:")
            print("   1. 检查生成的 TSX 文件内容是否正确")
            print("   2. 测试前端预览功能")
            print(f"   3. 使用 Task ID '{task_id}' 在前端预览")
            return True
            
        elif video_status == "skipped":
            reason = video_info.get("reason", "Unknown")
            print(f"⚠️  TSX 组件生成被跳过")
            print(f"   原因: {reason}")
            print()
            print("💡 提示:")
            print("   - 这通常是因为 Remotion 环境不可用")
            print("   - 或者 pipeline_full_video.py 脚本未找到")
            print("   - 检查后端日志以获取详细信息")
            return False
            
        elif video_status == "failed":
            error = video_info.get("error", "Unknown error")
            print(f"❌ TSX 组件生成失败")
            print(f"   错误: {error[:500]}")
            print()
            print("💡 提示:")
            print("   - 检查后端日志以获取详细错误信息")
            print("   - 确认 pipeline_full_video.py 脚本存在")
            print("   - 确认 Remotion 环境配置正确")
            return False
            
        else:
            print(f"⚠️  未知状态: {video_status}")
            return False
            
    except Exception as e:
        print()
        print("=" * 70)
        print("❌ 测试失败")
        print("=" * 70)
        print(f"错误: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_backend_video_generation()
    sys.exit(0 if success else 1)
