"""
🎬 NL2DV 完整流水线 - 从自然语言到完整视频

一键完成：自然语言 + DataFrame → 配置生成 → 视频生成

使用方法：
    # 方式1: 命令行（推荐）
    python -m deepeye.nodes.nl2dv.pipeline \\
        --query "生成一个展示销售趋势的视频" \\
        --data data.csv \\
        --output-dir ./output
    
    # 方式2: 使用已有配置
    python -m deepeye.nodes.nl2dv.pipeline \\
        --config config.json \\
        --skip-config-generation

参数说明：
    --query: 自然语言任务描述
    --data: 数据文件路径（CSV/JSON/Excel）或 DataFrame
    --config: 配置文件路径（如果已有配置，可跳过生成）
    --output-dir: 输出目录（默认：./output）
    --workers: 并行线程数（默认：5）
    --language: 输出语言（English/Chinese，默认：English）
    --skip-config-generation: 跳过配置生成，直接使用已有配置
    --skip-static: 跳过静态图生成
    --skip-animation: 跳过动画生成
    --skip-other-scenes: 跳过其他场景生成（opening/closing/stat_cards）
"""

import os
import sys
import json
import argparse
import subprocess
import time
from pathlib import Path
from datetime import datetime
from typing import Optional, Union

import pandas as pd

# 添加项目路径
current_dir = Path(__file__).parent
# pipeline.py 在 deepeye/nodes/nl2dv/ 下
# 需要找到 deepeye-core 目录（向上3级）
deepeye_core_dir = current_dir.parent.parent.parent
sys.path.insert(0, str(deepeye_core_dir))

from deepeye.nodes.nl2dv import NL2DVNode
from deepeye.nodes.io import NodeInput


def load_data(data_path: Union[str, Path]) -> pd.DataFrame:
    """加载数据文件"""
    data_path = Path(data_path)
    
    if not data_path.exists():
        raise FileNotFoundError(f"数据文件不存在: {data_path}")
    
    suffix = data_path.suffix.lower()
    
    if suffix == '.csv':
        return pd.read_csv(data_path)
    elif suffix == '.json':
        return pd.read_json(data_path)
    elif suffix in ['.xlsx', '.xls']:
        return pd.read_excel(data_path)
    else:
        raise ValueError(f"不支持的文件格式: {suffix}，支持: .csv, .json, .xlsx, .xls")


def save_config(config: dict, output_dir: Path) -> Path:
    """保存配置到文件"""
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 生成带时间戳的文件名
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    config_file = output_dir / f"nl2dv_config_{timestamp}.json"
    
    with open(config_file, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)
    
    return config_file


def run_command(cmd: str, description: str) -> bool:
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


def generate_config(
    query: str,
    dataframe: pd.DataFrame,
    output_dir: Path,
    api_key: Optional[str] = None,
    base_url: str = "https://api.openai.com/v1",
    model: str = "gpt-4o",
    language: str = "English",
    skip_animations: bool = False,
    verbose: bool = True
) -> Path:
    """生成视频配置"""
    print("\n" + "="*70)
    print("📝 阶段1: 生成视频配置")
    print("="*70)
    
    # 从环境变量读取 API Key（如果未提供）
    if not api_key:
        api_key = os.getenv("DEEPEYE_LLM_API_KEY")
        if not api_key:
            raise ValueError(
                "未提供 API Key！请通过 --api-key 参数或设置 DEEPEYE_LLM_API_KEY 环境变量"
            )
    
    # 确保 base_url 包含 /v1
    if base_url and not base_url.endswith("/v1"):
        base_url = f"{base_url.rstrip('/')}/v1"
    
    # 创建 NL2DV 节点
    print(f"\n🔧 创建 NL2DV 节点...")
    print(f"   模型: {model}")
    print(f"   语言: {language}")
    print(f"   跳过动画: {skip_animations}")
    
    node = NL2DVNode(
        node_id="pipeline_nl2dv",
        config={
            "api_key": api_key,
            "base_url": base_url,
            "model": model,
            "language": language,
            "skip_animations": skip_animations,
            "verbose": verbose
        }
    )
    
    # 执行节点生成配置
    print(f"\n🚀 执行配置生成...")
    print(f"   任务描述: {query}")
    print(f"   数据形状: {dataframe.shape}")
    
    outputs = node.run({
        "data": NodeInput(data={"dataframe": dataframe}),
        "task": NodeInput(data={"description": query})
    })
    
    result = outputs["config"]
    
    if result.status != "success":
        error_msg = result.metadata.get("error", "未知错误")
        raise RuntimeError(f"配置生成失败: {error_msg}")
    
    config = result.data
    
    print(f"\n✅ 配置生成成功！")
    print(f"   视频标题: {config.get('meta', {}).get('title', 'N/A')}")
    print(f"   场景数量: {len(config.get('scenes', []))}")
    
    # 保存配置
    config_file = save_config(config, output_dir)
    print(f"\n💾 配置已保存到: {config_file}")
    
    return config_file


def generate_video(
    config_file: Path,
    output_dir: Path,
    workers: int = 5,
    skip_static: bool = False,
    skip_animation: bool = False,
    skip_other_scenes: bool = False
):
    """生成完整视频"""
    print("\n" + "="*70)
    print("🎬 阶段2: 生成完整视频")
    print("="*70)
    
    # 获取 video_generation 目录
    video_gen_dir = current_dir / "video_generation"
    pipeline_script = video_gen_dir / "pipeline_full_video.py"
    
    if not pipeline_script.exists():
        raise FileNotFoundError(f"视频生成脚本不存在: {pipeline_script}")
    
    # 构建命令
    cmd_parts = [
        f'python "{pipeline_script}"',
        f'--config "{config_file}"',
        f'--workers {workers}'
    ]
    
    if skip_static:
        cmd_parts.append("--skip-static")
    if skip_animation:
        cmd_parts.append("--skip-animation")
    if skip_other_scenes:
        cmd_parts.append("--skip-other-scenes")
    
    cmd = " ".join(cmd_parts)
    
    # 执行视频生成
    if not run_command(cmd, "生成完整视频"):
        raise RuntimeError("视频生成失败！")
    
    print(f"\n✅ 视频生成完成！")
    print(f"   配置文件: {config_file}")
    print(f"   输出目录: {output_dir}")


def main():
    parser = argparse.ArgumentParser(
        description='NL2DV 完整流水线：从自然语言到完整视频',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    # 输入参数
    input_group = parser.add_argument_group('输入参数')
    input_group.add_argument('--query', type=str, help='自然语言任务描述')
    input_group.add_argument('--data', type=str, help='数据文件路径（CSV/JSON/Excel）')
    input_group.add_argument('--config', type=str, help='配置文件路径（如果已有配置）')
    
    # LLM 配置
    llm_group = parser.add_argument_group('LLM 配置')
    llm_group.add_argument('--api-key', type=str, help='LLM API Key（或设置 DEEPEYE_LLM_API_KEY 环境变量）')
    llm_group.add_argument('--base-url', type=str, default="https://api.openai.com/v1", help='LLM API Base URL')
    llm_group.add_argument('--model', type=str, default="gpt-4o", help='LLM 模型名称')
    llm_group.add_argument('--language', type=str, default="English", choices=["English", "Chinese"], help='输出语言')
    
    # 输出配置
    output_group = parser.add_argument_group('输出配置')
    output_group.add_argument('--output-dir', type=str, default="./output", help='输出目录（默认：./output）')
    output_group.add_argument('--workers', type=int, default=5, help='并行线程数（默认：5）')
    
    # 生成选项
    gen_group = parser.add_argument_group('生成选项')
    gen_group.add_argument('--skip-config-generation', action='store_true', help='跳过配置生成，直接使用已有配置')
    gen_group.add_argument('--skip-animations', action='store_true', help='配置生成时跳过动画生成')
    gen_group.add_argument('--skip-static', action='store_true', help='跳过静态图生成')
    gen_group.add_argument('--skip-animation', action='store_true', help='跳过动画生成')
    gen_group.add_argument('--skip-other-scenes', action='store_true', help='跳过其他场景生成（opening/closing/stat_cards）')
    gen_group.add_argument('--verbose', action='store_true', help='显示详细日志')
    
    args = parser.parse_args()
    
    # 验证参数
    if not args.skip_config_generation:
        if not args.query:
            parser.error("--query 参数是必需的（除非使用 --skip-config-generation）")
        if not args.data:
            parser.error("--data 参数是必需的（除非使用 --skip-config-generation）")
    else:
        if not args.config:
            parser.error("使用 --skip-config-generation 时必须提供 --config 参数")
    
    # 准备输出目录
    output_dir = Path(args.output_dir).absolute()
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print("🎬"*30)
    print("🎥 NL2DV 完整流水线")
    print("🎬"*30)
    print(f"\n📁 输出目录: {output_dir}")
    
    total_start = time.time()
    
    try:
        # 阶段1: 生成配置（如果需要）
        if not args.skip_config_generation:
            # 加载数据
            print(f"\n📊 加载数据文件: {args.data}")
            dataframe = load_data(args.data)
            print(f"   数据形状: {dataframe.shape}")
            print(f"   列: {list(dataframe.columns)}")
            
            # 生成配置
            config_file = generate_config(
                query=args.query,
                dataframe=dataframe,
                output_dir=output_dir,
                api_key=args.api_key,
                base_url=args.base_url,
                model=args.model,
                language=args.language,
                skip_animations=args.skip_animations,
                verbose=args.verbose
            )
        else:
            # 使用已有配置
            config_file = Path(args.config).absolute()
            if not config_file.exists():
                raise FileNotFoundError(f"配置文件不存在: {config_file}")
            print(f"\n📋 使用已有配置: {config_file}")
        
        # 阶段2: 生成视频
        generate_video(
            config_file=config_file,
            output_dir=output_dir,
            workers=args.workers,
            skip_static=args.skip_static,
            skip_animation=args.skip_animation,
            skip_other_scenes=args.skip_other_scenes
        )
        
        # 完成！
        total_elapsed = time.time() - total_start
        
        print(f"\n{'='*70}")
        print(f"🎉 流水线执行完成！")
        print(f"{'='*70}")
        print(f"⏱️  总耗时: {total_elapsed:.1f}秒 ({total_elapsed/60:.1f}分钟)")
        print(f"\n💡 下一步：")
        print(f"   1. 在 Remotion Studio 中查看完整视频")
        print(f"   2. 可以预览单个场景或完整串联视频")
        print(f"   3. 如果 Remotion Studio 未运行，执行: npm start")
        print(f"\n📁 输出文件：")
        print(f"   配置文件: {config_file}")
        print(f"   输出目录: {output_dir}")
        
    except Exception as e:
        print(f"\n❌ 流水线执行失败: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()

