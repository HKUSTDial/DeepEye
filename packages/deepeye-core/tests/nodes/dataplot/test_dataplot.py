"""DataPlotNode 单元测试

这个测试文件使用 mock 来测试 DataPlotNode 的功能,不需要真实的 API Key 或 Docker 环境。
"""

import pytest
import pandas as pd
import os
from unittest.mock import MagicMock, patch

from deepeye.nodes.dataplot import DataPlotNode
from deepeye.nodes.io import NodeInput
from deepeye.nodes.base import NodeStatus


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def mock_llm_client():
    """Mock LLM 客户端"""
    with patch('deepeye.nodes.dataplot.dataplot.LLMClient') as mock:
        yield mock


@pytest.fixture
def mock_executor():
    """Mock PlotCodeExecutor"""
    with patch('deepeye.nodes.dataplot.dataplot.PlotCodeExecutor') as mock:
        yield mock


@pytest.fixture
def mock_workspace_manager():
    """Mock WorkspaceManager"""
    with patch('deepeye.nodes.dataplot.dataplot.WorkspaceManager') as mock:
        yield mock


@pytest.fixture
def sample_dataframe():
    """创建示例 DataFrame"""
    return pd.DataFrame({
        'month': ['Jan', 'Feb', 'Mar', 'Apr', 'May'],
        'sales': [100, 150, 120, 180, 200],
        'costs': [80, 100, 90, 120, 130]
    })


@pytest.fixture
def sample_dataframes():
    """创建多个示例 DataFrame"""
    df1 = pd.DataFrame({
        'x': [1, 2, 3, 4, 5],
        'y': [2, 4, 6, 8, 10]
    })
    
    df2 = pd.DataFrame({
        'category': ['A', 'B', 'C', 'D'],
        'value': [10, 20, 15, 25]
    })
    
    return [df1, df2]


# ============================================================================
# 测试：节点初始化
# ============================================================================

class TestDataPlotNodeInit:
    """测试 DataPlotNode 初始化"""
    
    def test_init_with_api_key(self, mock_llm_client, mock_executor, mock_workspace_manager):
        """测试使用 API Key 初始化"""
        node = DataPlotNode(
            node_id="plot1",
            config={
                "api_key": "test-key",
                "model": "gpt-4",
                "verbose": True
            }
        )
        
        assert node.node_id == "plot1"
        assert node.node_type == "DataPlot"
        assert node.config.api_key == "test-key"
        assert node.config.model == "gpt-4"
        assert node.config.verbose is True
        
        # 验证 LLM 客户端被正确初始化
        mock_llm_client.assert_called_once()
    
    def test_init_with_env_api_key(self, mock_llm_client, mock_executor, mock_workspace_manager):
        """测试从环境变量读取 API Key"""
        with patch.dict(os.environ, {"DEEPEYE_LLM_API_KEY": "env-test-key"}):
            node = DataPlotNode(
                node_id="plot2",
                config={}
            )
            
            assert node.node_id == "plot2"
            mock_llm_client.assert_called_once()
    
    def test_init_without_api_key(self, mock_llm_client, mock_executor, mock_workspace_manager):
        """测试没有 API Key 时可以正常初始化（延迟验证）"""
        with patch.dict(os.environ, {}, clear=True):
            # 节点应该可以正常创建，API Key 验证延迟到执行时
            node = DataPlotNode(config={})
            assert node is not None
            assert node.llm_client is not None
    
    def test_init_with_custom_params(self, mock_llm_client, mock_executor, mock_workspace_manager):
        """测试自定义参数初始化"""
        config = {
            "api_key": "test-key",
            "base_url": "https://custom.api.com/v1",
            "model": "gpt-3.5-turbo",
            "temperature": 0.2,
            "max_retries": 5,
            "timeout": 120,
            "libraries": ["matplotlib", "plotly"],
            "sandbox_plot_dir": "/custom/plots",
            "verbose": True
        }
        
        node = DataPlotNode(node_id="plot3", config=config)
        
        assert node.config.base_url == "https://custom.api.com/v1"
        assert node.config.model == "gpt-3.5-turbo"
        assert node.config.temperature == 0.2
        assert node.config.max_retries == 5
        assert node.config.timeout == 120
        assert node.config.libraries == ["matplotlib", "plotly"]
        assert node.config.sandbox_plot_dir == "/custom/plots"
    
    def test_metadata(self, mock_llm_client, mock_executor, mock_workspace_manager):
        """测试节点元数据"""
        node = DataPlotNode(config={"api_key": "test-key"})
        
        assert node.metadata.name == "DataPlot"
        assert node.metadata.display_name == "智能数据可视化"
        assert node.metadata.category == "visualization"
        assert "llm" in node.metadata.tags
        assert "visualization" in node.metadata.tags
        
        # 检查输入端口
        assert len(node.input_ports) == 2
        port_names = [port.name for port in node.input_ports]
        assert "data" in port_names
        assert "task" in port_names
        
        # 检查输出端口
        assert len(node.output_ports) == 1
        assert node.output_ports[0].name == "images"


# ============================================================================
# 测试：执行功能
# ============================================================================

class TestDataPlotNodeExecute:
    """测试 DataPlotNode 执行功能"""
    
    def test_execute_success_first_try(
        self, 
        mock_llm_client, 
        mock_executor, 
        mock_workspace_manager,
        sample_dataframe
    ):
        """测试第一次尝试就成功"""
        # Mock LLM 响应
        mock_client_instance = MagicMock()
        mock_llm_client.return_value = mock_client_instance
        
        mock_response = MagicMock()
        mock_response.content = """
<think>
需要创建一个折线图显示销售趋势
</think>

<package_list>
matplotlib, seaborn
</package_list>

<code>
import matplotlib.pyplot as plt

fig, ax = plt.subplots(figsize=(10, 6))
ax.plot(df['month'], df['sales'], marker='o')
ax.set_title('Monthly Sales Trend')
ax.set_xlabel('Month')
ax.set_ylabel('Sales')

filename = 'sales_trend.png'
plt.savefig(f'{PLOT_DIR}/{filename}', dpi=300, bbox_inches='tight')
plt.close()

print(f'PLOT_FILE: {filename}|Monthly sales trend line chart|png')
</code>
"""
        mock_client_instance.generate.return_value = mock_response
        
        # Mock Executor 响应
        mock_executor_instance = MagicMock()
        mock_executor.return_value = mock_executor_instance
        
        mock_images = [{
            "data": b"fake_image_data",
            "filename": "sales_trend.png",
            "description": "Monthly sales trend line chart",
            "format": "png",
            "file_size": 1024,
            "file_path": "/workspace/plots/sales_trend.png"
        }]
        mock_executor_instance.execute.return_value = (True, mock_images, None)
        
        # 创建节点并执行
        node = DataPlotNode(config={"api_key": "test-key"})
        
        inputs = {
            "data": NodeInput(data={"dataframe": sample_dataframe}),
            "task": NodeInput(data={"description": "绘制月度销售额折线图"})
        }
        
        outputs = node.run(inputs)
        result_output = outputs["images"]
        
        # 验证结果
        assert result_output.status == NodeStatus.SUCCESS
        assert result_output.metrics["retries"] == 0
        assert result_output.metadata["image_count"] == 1
        assert len(result_output.data) == 1
        
        image = result_output.data[0]
        assert image["filename"] == "sales_trend.png"
        assert image["data"] == b"fake_image_data"
        assert image["format"] == "png"
        assert image["file_size"] == 1024
    
    def test_execute_success_after_retry(
        self, 
        mock_llm_client, 
        mock_executor, 
        mock_workspace_manager,
        sample_dataframe
    ):
        """测试第一次失败，重试后成功"""
        mock_client_instance = MagicMock()
        mock_llm_client.return_value = mock_client_instance
        
        # 第一次生成的代码
        initial_response = MagicMock()
        initial_response.content = """
<think>
创建折线图
</think>

<package_list>
matplotlib
</package_list>

<code>
import matplotlib.pyplot as plt
plt.plot(df['month'], df['sales'])
plt.savefig(f'{PLOT_DIR}/sales.png')
# 忘记打印 PLOT_FILE 标记
</code>
"""
        
        # 修复后的代码
        fixed_response = MagicMock()
        fixed_response.content = """
<think>
需要添加 PLOT_FILE 标记
</think>

<package_list>
matplotlib
</package_list>

<code>
import matplotlib.pyplot as plt
plt.plot(df['month'], df['sales'])
filename = 'sales.png'
plt.savefig(f'{PLOT_DIR}/{filename}')
plt.close()
print(f'PLOT_FILE: {filename}|Sales chart|png')
</code>
"""
        
        mock_client_instance.generate.side_effect = [initial_response, fixed_response]
        
        # Mock Executor
        mock_executor_instance = MagicMock()
        mock_executor.return_value = mock_executor_instance
        
        mock_images = [{
            "data": b"fixed_image",
            "filename": "sales.png",
            "description": "Sales chart",
            "format": "png",
            "file_size": 2048,
            "file_path": "/workspace/plots/sales.png"
        }]
        
        # 第一次失败，第二次成功
        mock_executor_instance.execute.side_effect = [
            (False, None, "未找到图片信息标记"),
            (True, mock_images, None)
        ]
        
        node = DataPlotNode(config={"api_key": "test-key", "max_retries": 2})
        
        inputs = {
            "data": NodeInput(data={"dataframe": sample_dataframe}),
            "task": NodeInput(data={"description": "绘制销售图"})
        }
        
        outputs = node.run(inputs)
        result_output = outputs["images"]
        
        assert result_output.status == NodeStatus.SUCCESS
        assert result_output.metrics["retries"] == 1
        assert len(result_output.data) == 1
    
    def test_execute_failure_max_retries(
        self, 
        mock_llm_client, 
        mock_executor, 
        mock_workspace_manager,
        sample_dataframe
    ):
        """测试达到最大重试次数后失败"""
        mock_client_instance = MagicMock()
        mock_llm_client.return_value = mock_client_instance
        
        # 所有尝试都返回相同的错误代码
        mock_response = MagicMock()
        mock_response.content = """
<think>
尝试创建图表
</think>

<package_list>
matplotlib
</package_list>

<code>
import matplotlib.pyplot as plt
# 错误的代码
plt.plot(df['nonexistent_column'])
</code>
"""
        mock_client_instance.generate.return_value = mock_response
        
        # Mock Executor 总是失败
        mock_executor_instance = MagicMock()
        mock_executor.return_value = mock_executor_instance
        mock_executor_instance.execute.return_value = (
            False, 
            None, 
            "KeyError: 'nonexistent_column'"
        )
        
        node = DataPlotNode(config={"api_key": "test-key", "max_retries": 2})
        
        inputs = {
            "data": NodeInput(data={"dataframe": sample_dataframe}),
            "task": NodeInput(data={"description": "绘制图表"})
        }
        
        outputs = node.run(inputs)
        result_output = outputs["images"]
        
        # 执行失败后状态应该是 FAILED
        assert result_output.status == NodeStatus.FAILED
        assert result_output.metrics["retries"] == 2
        assert result_output.error is not None
        assert "KeyError" in result_output.error
    
    def test_execute_multi_dataframe_mode(
        self, 
        mock_llm_client, 
        mock_executor, 
        mock_workspace_manager,
        sample_dataframes
    ):
        """测试多 DataFrame 模式"""
        mock_client_instance = MagicMock()
        mock_llm_client.return_value = mock_client_instance
        
        mock_response = MagicMock()
        mock_response.content = """
<think>
创建两个子图
</think>

<package_list>
matplotlib
</package_list>

<code>
import matplotlib.pyplot as plt

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
ax1.scatter(df0['x'], df0['y'])
ax2.bar(df1['category'], df1['value'])

filename = 'comparison.png'
plt.savefig(f'{PLOT_DIR}/{filename}')
plt.close()
print(f'PLOT_FILE: {filename}|Comparison chart|png')
</code>
"""
        mock_client_instance.generate.return_value = mock_response
        
        mock_executor_instance = MagicMock()
        mock_executor.return_value = mock_executor_instance
        
        mock_images = [{
            "data": b"comparison_image",
            "filename": "comparison.png",
            "description": "Comparison chart",
            "format": "png",
            "file_size": 3072,
            "file_path": "/workspace/plots/comparison.png"
        }]
        mock_executor_instance.execute.return_value = (True, mock_images, None)
        
        node = DataPlotNode(config={"api_key": "test-key"})
        
        inputs = {
            "data": NodeInput(data={"dataframe_list": sample_dataframes}),
            "task": NodeInput(data={"description": "创建对比图"})
        }
        
        outputs = node.run(inputs)
        result_output = outputs["images"]
        
        assert result_output.status == NodeStatus.SUCCESS
        assert result_output.metadata["is_multi_mode"] is True
        assert result_output.metadata["num_dataframes"] == 2
        assert result_output.metadata["input_shapes"] == [(5, 2), (4, 2)]
    
    def test_execute_invalid_input_missing_field(
        self, 
        mock_llm_client, 
        mock_executor, 
        mock_workspace_manager
    ):
        """测试缺少必需字段的输入"""
        node = DataPlotNode(config={"api_key": "test-key"})
        
        inputs = {
            "data": NodeInput(data={}),  # 缺少 dataframe 或 dataframe_list
            "task": NodeInput(data={"description": "绘制图表"})
        }
        
        outputs = node.run(inputs)
        result_output = outputs["images"]
        
        # execute 方法返回时应该标记为 FAILED
        assert result_output.status == NodeStatus.FAILED
        assert result_output.error is not None
        assert "必须提供" in result_output.error
    
    def test_execute_invalid_input_type(
        self, 
        mock_llm_client, 
        mock_executor, 
        mock_workspace_manager
    ):
        """测试无效的输入类型"""
        node = DataPlotNode(config={"api_key": "test-key"})
        
        # 传入非 DataFrame 对象
        inputs = {
            "data": NodeInput(data={"dataframe": "not a dataframe"}),
            "task": NodeInput(data={"description": "绘制图表"})
        }
        
        outputs = node.run(inputs)
        result_output = outputs["images"]
        
        # execute 方法返回时应该标记为 FAILED
        assert result_output.status == NodeStatus.FAILED
        assert result_output.error is not None
        assert "DataFrame" in result_output.error
    
    def test_execute_invalid_task_type(
        self, 
        mock_llm_client, 
        mock_executor, 
        mock_workspace_manager,
        sample_dataframe
    ):
        """测试无效的任务描述类型"""
        node = DataPlotNode(config={"api_key": "test-key"})
        
        inputs = {
            "data": NodeInput(data={"dataframe": sample_dataframe}),
            "task": NodeInput(data={"description": 123})  # 应该是字符串
        }
        
        outputs = node.run(inputs)
        result_output = outputs["images"]
        
        # 输入验证失败时,BaseNode.run 会捕获异常并设置 FAILED 状态
        # 错误信息在 error 字段而不是 metadata
        assert result_output.status == NodeStatus.FAILED
        assert result_output.error is not None
        assert "description" in result_output.error
    
    def test_execute_multiple_images(
        self, 
        mock_llm_client, 
        mock_executor, 
        mock_workspace_manager,
        sample_dataframe
    ):
        """测试生成多个图片"""
        mock_client_instance = MagicMock()
        mock_llm_client.return_value = mock_client_instance
        
        mock_response = MagicMock()
        mock_response.content = """
<think>
创建两个图表
</think>

<package_list>
matplotlib
</package_list>

<code>
import matplotlib.pyplot as plt

# 图表1
plt.figure()
plt.plot(df['month'], df['sales'])
plt.savefig(f'{PLOT_DIR}/sales.png')
plt.close()
print('PLOT_FILE: sales.png|Sales trend|png')

# 图表2
plt.figure()
plt.bar(df['month'], df['costs'])
plt.savefig(f'{PLOT_DIR}/costs.png')
plt.close()
print('PLOT_FILE: costs.png|Costs bar chart|png')
</code>
"""
        mock_client_instance.generate.return_value = mock_response
        
        mock_executor_instance = MagicMock()
        mock_executor.return_value = mock_executor_instance
        
        mock_images = [
            {
                "data": b"sales_image",
                "filename": "sales.png",
                "description": "Sales trend",
                "format": "png",
                "file_size": 1024,
                "file_path": "/workspace/plots/sales.png"
            },
            {
                "data": b"costs_image",
                "filename": "costs.png",
                "description": "Costs bar chart",
                "format": "png",
                "file_size": 1536,
                "file_path": "/workspace/plots/costs.png"
            }
        ]
        mock_executor_instance.execute.return_value = (True, mock_images, None)
        
        node = DataPlotNode(config={"api_key": "test-key"})
        
        inputs = {
            "data": NodeInput(data={"dataframe": sample_dataframe}),
            "task": NodeInput(data={"description": "创建销售和成本图表"})
        }
        
        outputs = node.run(inputs)
        result_output = outputs["images"]
        
        assert result_output.status == NodeStatus.SUCCESS
        assert result_output.metadata["image_count"] == 2
        assert len(result_output.data) == 2
        assert result_output.data[0]["filename"] == "sales.png"
        assert result_output.data[1]["filename"] == "costs.png"


# ============================================================================
# 测试：辅助方法
# ============================================================================

class TestDataPlotNodeHelperMethods:
    """测试 DataPlotNode 辅助方法"""
    
    def test_get_dataframe_info(
        self, 
        mock_llm_client, 
        mock_executor, 
        mock_workspace_manager,
        sample_dataframe
    ):
        """测试 DataFrame 信息生成"""
        node = DataPlotNode(config={"api_key": "test-key"})
        
        info = node._get_dataframe_info(sample_dataframe)
        
        assert "形状: (5, 3)" in info
        assert "列信息:" in info
        assert "month" in info
        assert "sales" in info
        assert "costs" in info
        assert "前 5 行数据" in info
        assert "Jan" in info
    
    def test_get_multi_dataframe_info(
        self, 
        mock_llm_client, 
        mock_executor, 
        mock_workspace_manager,
        sample_dataframes
    ):
        """测试多 DataFrame 信息生成"""
        node = DataPlotNode(config={"api_key": "test-key"})
        
        info = node._get_multi_dataframe_info(sample_dataframes)
        
        assert "共有 2 个 DataFrame" in info
        assert "DataFrame 0" in info
        assert "DataFrame 1" in info
        assert "df0" in info
        assert "df1" in info
        assert "形状: (5, 2)" in info
        assert "形状: (4, 2)" in info


# ============================================================================
# 测试：边界情况
# ============================================================================

class TestDataPlotNodeEdgeCases:
    """测试 DataPlotNode 边界情况"""
    
    def test_empty_dataframe(
        self, 
        mock_llm_client, 
        mock_executor, 
        mock_workspace_manager
    ):
        """测试空 DataFrame"""
        empty_df = pd.DataFrame()
        
        mock_client_instance = MagicMock()
        mock_llm_client.return_value = mock_client_instance
        
        mock_response = MagicMock()
        mock_response.content = """
<think>
DataFrame 为空，无法绘图
</think>

<package_list>
matplotlib
</package_list>

<code>
import matplotlib.pyplot as plt
print("Warning: Empty DataFrame")
</code>
"""
        mock_client_instance.generate.return_value = mock_response
        
        mock_executor_instance = MagicMock()
        mock_executor.return_value = mock_executor_instance
        mock_executor_instance.execute.return_value = (
            False, 
            None, 
            "Cannot plot empty DataFrame"
        )
        
        node = DataPlotNode(config={"api_key": "test-key"})
        
        inputs = {
            "data": NodeInput(data={"dataframe": empty_df}),
            "task": NodeInput(data={"description": "绘制图表"})
        }
        
        outputs = node.run(inputs)
        result_output = outputs["images"]
        
        # 执行失败后应该标记为 FAILED
        assert result_output.status == NodeStatus.FAILED
        assert result_output.error is not None
    
    def test_large_dataframe_info(
        self, 
        mock_llm_client, 
        mock_executor, 
        mock_workspace_manager
    ):
        """测试大型 DataFrame 的信息提取"""
        large_df = pd.DataFrame({
            f'col_{i}': range(1000) for i in range(50)
        })
        
        node = DataPlotNode(config={"api_key": "test-key"})
        info = node._get_dataframe_info(large_df)
        
        assert "形状: (1000, 50)" in info
        assert "前 5 行数据" in info
    
    def test_dataframe_with_nulls(
        self, 
        mock_llm_client, 
        mock_executor, 
        mock_workspace_manager
    ):
        """测试包含空值的 DataFrame"""
        df_with_nulls = pd.DataFrame({
            'a': [1, 2, None, 4, 5],
            'b': [None, 'x', 'y', 'z', None]
        })
        
        node = DataPlotNode(config={"api_key": "test-key"})
        info = node._get_dataframe_info(df_with_nulls)
        
        assert "空值" in info
        assert "形状: (5, 2)" in info
    
    def test_dataframe_with_various_dtypes(
        self, 
        mock_llm_client, 
        mock_executor, 
        mock_workspace_manager
    ):
        """测试包含多种数据类型的 DataFrame"""
        df = pd.DataFrame({
            'int_col': [1, 2, 3],
            'float_col': [1.1, 2.2, 3.3],
            'str_col': ['a', 'b', 'c'],
            'bool_col': [True, False, True]
        })
        
        node = DataPlotNode(config={"api_key": "test-key"})
        info = node._get_dataframe_info(df)
        
        assert "int_col" in info
        assert "float_col" in info
        assert "str_col" in info
        assert "bool_col" in info


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v", "-s"])

