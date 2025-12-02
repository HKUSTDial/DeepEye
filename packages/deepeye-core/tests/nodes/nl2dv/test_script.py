"""NL2DV 节点快速测试脚本

直接测试 NL2DV 节点是否能正常生成视频配置脚本
"""

import os
import sys
import json
import pandas as pd
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from deepeye.nodes.nl2dv import NL2DVNode
from deepeye.nodes.io import NodeInput

# 加载 .env 文件（从项目根目录）
env_path = project_root / ".env"
if env_path.exists():
    load_dotenv(env_path)
else:
    # 如果项目根目录没有 .env，尝试从当前目录向上查找
    current = Path(__file__).parent
    while current != current.parent:
        env_file = current / ".env"
        if env_file.exists():
            load_dotenv(env_file)
            break
        current = current.parent

# 从环境变量读取配置
API_KEY = os.getenv("DEEPEYE_LLM_API_KEY")
API_BASE = os.getenv("DEEPEYE_LLM_BASE_URL", "https://api.openai.com")
MODEL = os.getenv("DEEPEYE_LLM_MODEL", "gpt-4o")

# 确保 base_url 包含 /v1 路径
if API_BASE and not API_BASE.endswith("/v1"):
    API_BASE = f"{API_BASE.rstrip('/')}/v1"

def test_nl2dv_basic():
    """测试基本 NL2DV 功能"""
    print("=" * 60)
    print("测试 NL2DV 节点生成视频配置")
    print("=" * 60)
    
    # 检查配置
    if not API_KEY:
        print("❌ 错误: 未设置 DEEPEYE_LLM_API_KEY 环境变量")
        print("   请在 .env 文件中设置 DEEPEYE_LLM_API_KEY")
        return
    
    print(f"\n✅ 配置检查通过:")
    print(f"   API Key: {API_KEY[:20]}...")
    print(f"   Base URL: {API_BASE}")
    print(f"   Model: {MODEL}")
    
    # 准备测试数据
    print("\n📊 准备测试数据...")
    df = pd.DataFrame({
        'company': ['Apple', 'Microsoft', 'Google', 'Amazon', 'Meta'],
        'revenue': [394.3, 211.9, 307.4, 514.0, 134.9],
        'employees': [164000, 221000, 190234, 1541000, 86482]
    })
    print(f"   数据形状: {df.shape}")
    print(f"   列: {list(df.columns)}")
    print("\n   数据预览:")
    print(df.head())
    
    # 创建 NL2DV 节点
    print("\n🔧 创建 NL2DV 节点...")
    node = NL2DVNode(
        node_id="test_nl2dv",
        config={
            "api_key": API_KEY,
            "base_url": API_BASE,
            "model": MODEL,
            "language": "English",
            "verbose": True
        }
    )
    print("   ✅ 节点创建成功")
    
    # 执行节点
    print("\n🚀 执行 NL2DV 节点生成视频配置...")
    print("   任务描述: 生成一个展示科技公司收入和员工数量的视频")
    
    try:
        outputs = node.run({
            "data": NodeInput(data={"dataframe": df}),
            "task": NodeInput(data={
                "description": "生成一个展示科技公司收入和员工数量的视频"
            })
        })
        
        # 检查结果
        result = outputs["config"]
        
        if result.status == "success":
            print("\n✅ 成功生成视频配置！")
            
            config = result.data
            metadata = result.metadata
            
            print(f"\n📋 配置信息:")
            print(f"   视频标题: {config.get('meta', {}).get('title', 'N/A')}")
            print(f"   场景数量: {len(config.get('scenes', []))}")
            print(f"   语言: {metadata.get('language', 'N/A')}")
            print(f"   输入数据形状: {metadata.get('input_shape', 'N/A')}")
            print(f"   动画数量: {metadata.get('total_animations', 0)}")
            
            # 显示场景信息
            print(f"\n🎬 场景列表:")
            for i, scene in enumerate(config.get('scenes', []), 1):
                scene_type = scene.get('type', 'unknown')
                scene_id = scene.get('id', 'unknown')
                print(f"   {i}. {scene_id} ({scene_type})")
                
                # 如果是图表场景，显示图表类型
                if scene_type == 'chart':
                    chart_type = scene.get('content', {}).get('chart_type', 'unknown')
                    print(f"      图表类型: {chart_type}")
            
            # 保存配置到文件（节点目录下的 configs 文件夹）
            # 从测试目录定位到代码目录的 configs 文件夹
            # tests/nodes/nl2dv -> packages/deepeye-core -> deepeye/nodes/nl2dv
            code_dir = Path(__file__).parent.parent.parent.parent / "deepeye" / "nodes" / "nl2dv"
            configs_dir = code_dir / "configs"
            configs_dir.mkdir(parents=True, exist_ok=True)
            
            # 生成带时间戳的文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = configs_dir / f"nl2dv_config_{timestamp}.json"
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
            print(f"\n💾 配置已保存到: {output_file.absolute()}")
            
            # 显示配置摘要
            print(f"\n📄 配置摘要 (前500字符):")
            config_str = json.dumps(config, ensure_ascii=False, indent=2)
            print(config_str[:500] + "..." if len(config_str) > 500 else config_str)
            
        else:
            print(f"\n❌ 生成失败: {result.metadata.get('error', 'Unknown error')}")
            
    except Exception as e:
        print(f"\n❌ 执行出错: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_nl2dv_basic()

