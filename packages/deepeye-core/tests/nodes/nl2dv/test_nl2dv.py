"""NL2DV 节点集成测试

使用真实的 LLM API 进行端到端测试。
需要设置 API Key 和 Base URL。
"""

import os
from pathlib import Path
import pytest
import pandas as pd
from dotenv import load_dotenv
from deepeye.nodes.nl2dv import NL2DVNode
from deepeye.nodes.io import NodeInput

# 加载 .env 文件
env_path = Path(__file__).parent.parent.parent.parent / ".env"
load_dotenv(env_path)

# 从环境变量读取配置
API_KEY = os.getenv("DEEPEYE_LLM_API_KEY")
API_BASE = os.getenv("DEEPEYE_LLM_BASE_URL", "https://api.openai.com")
MODEL = os.getenv("DEEPEYE_LLM_MODEL", "gpt-4o")

# 确保 base_url 包含 /v1 路径
if API_BASE and not API_BASE.endswith("/v1"):
    API_BASE = f"{API_BASE.rstrip('/')}/v1"

# 检查必需的配置，如果没有设置则跳过所有测试
pytestmark = pytest.mark.skipif(
    not API_KEY,
    reason="需要设置 DEEPEYE_LLM_API_KEY 环境变量或 .env 文件中的配置"
)


@pytest.fixture
def sample_dataframe():
    """创建示例 DataFrame"""
    return pd.DataFrame({
        'company': ['Apple', 'Microsoft', 'Google', 'Amazon', 'Meta'],
        'revenue': [394.3, 211.9, 307.4, 514.0, 134.9],
        'employees': [164000, 221000, 190234, 1541000, 86482]
    })


@pytest.fixture
def sample_dataframe_list():
    """创建多个示例 DataFrame"""
    df1 = pd.DataFrame({
        'month': ['Jan', 'Feb', 'Mar', 'Apr'],
        'sales': [100, 150, 120, 180]
    })
    df2 = pd.DataFrame({
        'category': ['A', 'B', 'C'],
        'value': [10, 20, 15]
    })
    return [df1, df2]


@pytest.fixture
def nl2dv_node():
    """创建 NL2DV 节点实例"""
    return NL2DVNode(
        node_id="test_nl2dv",
        config={
            "api_key": API_KEY,
            "base_url": API_BASE,
            "model": MODEL,
            "temperature": 0.7,
            "language": "English",
            "verbose": True,  # 开启详细输出，方便调试
            "skip_animations": False
        }
    )


class TestNL2DVNodeInitialization:
    """测试节点初始化"""
    
    def test_node_initialization(self):
        """测试节点初始化"""
        node = NL2DVNode(
            node_id="test_init",
            config={
                "api_key": API_KEY,
                "base_url": API_BASE,
                "model": "gpt-4o"
            }
        )
        
        assert node.node_id == "test_init"
        assert node.config.model == "gpt-4o"
        assert node.config.base_url == API_BASE
        assert len(node.input_ports) == 2  # data 和 task
        assert len(node.output_ports) == 1  # config
    
    def test_node_initialization_with_env_key(self, monkeypatch):
        """测试从环境变量读取 API Key"""
        monkeypatch.setenv("DEEPEYE_LLM_API_KEY", API_KEY)
        
        node = NL2DVNode(
            node_id="test_env",
            config={
                "base_url": API_BASE,
                "model": "gpt-4o"
            }
        )
        
        # 节点应该能成功初始化（使用环境变量中的 API Key）
        # 注意：config.api_key 可能仍然是 None，但 llm_client 会使用环境变量中的 key
        assert node.llm_client is not None
        assert node.llm_client.api_key == API_KEY
    
    def test_node_initialization_missing_key(self):
        """测试缺少 API Key 时抛出错误"""
        with pytest.raises(ValueError, match="未提供 API Key"):
            NL2DVNode(
                node_id="test_no_key",
                config={
                    "base_url": API_BASE,
                    "model": "gpt-4o"
                }
            )


class TestNL2DVNodeBasic:
    """测试 NL2DV 节点基本功能"""
    
    def test_basic_generation(self, nl2dv_node, sample_dataframe):
        """测试基本的视频配置生成"""
        outputs = nl2dv_node.run({
            "data": NodeInput(data={"dataframe": sample_dataframe}),
            "task": NodeInput(data={"description": "Create a video showing company revenue comparison"})
        })
        
        # 验证输出状态
        assert outputs["config"].status == "success"
        
        # 验证配置结构
        config = outputs["config"].data
        assert config is not None
        assert "meta" in config
        assert "scenes" in config
        assert isinstance(config["scenes"], list)
        assert len(config["scenes"]) > 0
        
        # 验证 meta 信息
        meta = config["meta"]
        assert "title" in meta
        assert "fps" in meta
        assert "width" in meta
        assert "height" in meta
        
        # 验证场景
        for scene in config["scenes"]:
            assert "id" in scene
            assert "type" in scene
            assert "content" in scene
        
        # 验证 metadata
        metadata = outputs["config"].metadata
        assert metadata is not None
        assert "task_description" in metadata
        assert "language" in metadata
        assert "num_scenes" in metadata
    
    def test_chinese_language(self, sample_dataframe):
        """测试中文输出"""
        node = NL2DVNode(
            node_id="test_chinese",
            config={
                "api_key": API_KEY,
                "base_url": API_BASE,
                "model": MODEL,
                "language": "Chinese",
                "verbose": True
            }
        )
        
        outputs = node.run({
            "data": NodeInput(data={"dataframe": sample_dataframe}),
            "task": NodeInput(data={"description": "创建一个展示公司收入的视频"})
        })
        
        assert outputs["config"].status == "success"
        config = outputs["config"].data
        
        # 验证标题可能是中文
        title = config["meta"]["title"]
        assert len(title) > 0
    
    def test_skip_animations(self, sample_dataframe):
        """测试跳过动画生成"""
        node = NL2DVNode(
            node_id="test_no_anim",
            config={
                "api_key": API_KEY,
                "base_url": API_BASE,
                "model": MODEL,
                "skip_animations": True,
                "verbose": True
            }
        )
        
        outputs = node.run({
            "data": NodeInput(data={"dataframe": sample_dataframe}),
            "task": NodeInput(data={"description": "Create a simple video without animations"})
        })
        
        assert outputs["config"].status == "success"
        config = outputs["config"].data
        
        # 验证场景可能没有动画（或动画数量为0）
        total_animations = sum(
            len(scene.get("animations", []))
            for scene in config["scenes"]
        )
        # 跳过动画时，动画数量应该为0或很少
        assert total_animations == 0 or total_animations < 3


class TestNL2DVNodeMultipleDataFrames:
    """测试多 DataFrame 输入"""
    
    def test_multiple_dataframes(self, nl2dv_node, sample_dataframe_list):
        """测试多个 DataFrame 输入"""
        outputs = nl2dv_node.run({
            "data": NodeInput(data={"dataframe_list": sample_dataframe_list}),
            "task": NodeInput(data={"description": "Create a comparison video from multiple datasets"})
        })
        
        assert outputs["config"].status == "success"
        config = outputs["config"].data
        
        # 验证配置生成成功
        assert "scenes" in config
        assert len(config["scenes"]) > 0
        
        # 验证 metadata 中记录了多个 DataFrame
        metadata = outputs["config"].metadata
        assert metadata["num_dataframes"] == 2


class TestNL2DVNodeErrorHandling:
    """测试错误处理"""
    
    def test_missing_data_input(self, nl2dv_node):
        """测试缺少数据输入"""
        outputs = nl2dv_node.run({
            "task": NodeInput(data={"description": "Create a video"})
        })
        
        assert outputs["config"].status == "failed"
        assert outputs["config"].error is not None
    
    def test_missing_task_input(self, nl2dv_node, sample_dataframe):
        """测试缺少任务描述"""
        outputs = nl2dv_node.run({
            "data": NodeInput(data={"dataframe": sample_dataframe})
        })
        
        assert outputs["config"].status == "failed"
        assert outputs["config"].error is not None
    
    def test_empty_task_description(self, nl2dv_node, sample_dataframe):
        """测试空任务描述"""
        outputs = nl2dv_node.run({
            "data": NodeInput(data={"dataframe": sample_dataframe}),
            "task": NodeInput(data={"description": ""})
        })
        
        assert outputs["config"].status == "failed"
        assert "task 必须是非空字符串" in outputs["config"].error
    
    def test_invalid_dataframe_type(self, nl2dv_node):
        """测试无效的 DataFrame 类型"""
        outputs = nl2dv_node.run({
            "data": NodeInput(data={"dataframe": "not a dataframe"}),
            "task": NodeInput(data={"description": "Create a video"})
        })
        
        assert outputs["config"].status == "failed"
        assert outputs["config"].error is not None


class TestNL2DVNodeComplexScenarios:
    """测试复杂场景"""
    
    def test_complex_query(self, nl2dv_node, sample_dataframe):
        """测试复杂查询"""
        outputs = nl2dv_node.run({
            "data": NodeInput(data={"dataframe": sample_dataframe}),
            "task": NodeInput(data={
                "description": (
                    "Create a professional data video showing: "
                    "1. Company revenue comparison with bar chart, "
                    "2. Employee count analysis, "
                    "3. Revenue per employee ratio, "
                    "4. Include animations and smooth transitions"
                )
            })
        })
        
        assert outputs["config"].status == "success"
        config = outputs["config"].data
        
        # 验证生成了多个场景
        assert len(config["scenes"]) >= 2
        
        # 验证包含不同类型的场景
        scene_types = [scene["type"] for scene in config["scenes"]]
        assert "chart" in scene_types or "opening" in scene_types
    
    def test_large_dataframe(self, nl2dv_node):
        """测试大数据集"""
        # 创建较大的 DataFrame
        large_df = pd.DataFrame({
            'category': [f'Category_{i}' for i in range(50)],
            'value': list(range(50, 100))
        })
        
        outputs = nl2dv_node.run({
            "data": NodeInput(data={"dataframe": large_df}),
            "task": NodeInput(data={"description": "Visualize this large dataset"})
        })
        
        assert outputs["config"].status == "success"
        config = outputs["config"].data
        
        # 验证配置生成成功
        assert "scenes" in config
        assert len(config["scenes"]) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])

