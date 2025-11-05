"""DataCoder 节点测试"""

import pytest
import pandas as pd
import os
from unittest.mock import Mock, patch, MagicMock

from deepeye.nodes.datacoder import DataCoderNode
from deepeye.nodes.io import NodeInput, NodeOutput, NodeStatus
from deepeye.llm import LLMResponse


@pytest.fixture
def sample_df():
    """测试用的示例 DataFrame"""
    return pd.DataFrame({
        'name': ['Alice', 'Bob', 'Charlie', 'David', 'Eve'],
        'age': [25, 30, 35, 40, 45],
        'salary': [50000, 60000, 70000, 80000, 90000],
        'department': ['IT', 'HR', 'IT', 'Finance', 'IT']
    })


@pytest.fixture
def mock_llm_client():
    """Mock LLM 客户端"""
    with patch('deepeye.nodes.datacoder.datacoder.LLMClient') as mock_client:
        yield mock_client


@pytest.fixture
def mock_executor():
    """Mock CodeExecutor"""
    with patch('deepeye.nodes.datacoder.datacoder.DataFrameCodeExecutor') as mock_exec:
        yield mock_exec


class TestDataCoderNodeInit:
    """测试 DataCoderNode 初始化"""
    
    def test_init_with_api_key(self, mock_llm_client, mock_executor):
        """测试使用 API Key 初始化"""
        node = DataCoderNode(
            node_id="test-node",
            config={
                "api_key": "test-key",
                "base_url": "https://api.test.com/v1",
                "model": "gpt-4"
            }
        )
        
        assert node.node_id == "test-node"
        assert node.node_type == "DataCoder"
        assert node.config.model == "gpt-4"
        assert node.config.temperature == 0.1
        assert node.config.max_retries == 3
        
        # 验证端口定义
        assert len(node.input_ports) == 2
        assert node.input_ports[0].name == "data"
        assert node.input_ports[1].name == "task"
        assert len(node.output_ports) == 1
        assert node.output_ports[0].name == "result"
        
        # 验证 LLM 客户端被正确初始化
        mock_llm_client.assert_called_once()
        call_kwargs = mock_llm_client.call_args[1]
        assert call_kwargs['api_key'] == "test-key"
        assert call_kwargs['base_url'] == "https://api.test.com/v1"
    
    def test_init_with_env_api_key(self, mock_llm_client, mock_executor):
        """测试从环境变量读取 API Key"""
        with patch.dict(os.environ, {'OPENAI_API_KEY': 'env-key'}):
            node = DataCoderNode(
                config={}
            )
            
            mock_llm_client.assert_called_once()
            call_kwargs = mock_llm_client.call_args[1]
            assert call_kwargs['api_key'] == 'env-key'
    
    def test_init_without_api_key(self, mock_llm_client, mock_executor):
        """测试未提供 API Key 时抛出异常"""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="未提供 API Key"):
                DataCoderNode(config={})
    
    def test_init_with_custom_params(self, mock_llm_client, mock_executor):
        """测试自定义参数初始化"""
        node = DataCoderNode(
            config={
                "api_key": "test-key",
                "model": "gpt-3.5-turbo",
                "temperature": 0.5,
                "max_retries": 5,
                "libraries": ["pandas", "numpy"],
                "verbose": True,
                "timeout": 120
            }
        )
        
        assert node.config.model == "gpt-3.5-turbo"
        assert node.config.temperature == 0.5
        assert node.config.max_retries == 5
        assert node.config.verbose is True
        
        # 验证 CodeExecutor 被正确初始化
        mock_executor.assert_called_once()
        call_kwargs = mock_executor.call_args[1]
        assert call_kwargs['libraries'] == ["pandas", "numpy"]
        assert call_kwargs['verbose'] is True
        assert call_kwargs['timeout'] == 120
    
    def test_metadata(self, mock_llm_client, mock_executor):
        """测试节点元数据"""
        node = DataCoderNode(config={"api_key": "test-key"})
        
        assert node.metadata.name == "DataCoder"
        assert node.metadata.display_name == "智能数据处理器"
        assert node.metadata.category == "processing"
        assert "llm" in node.metadata.tags
        assert "code-generation" in node.metadata.tags


class TestDataCoderNodeExecute:
    """测试 DataCoderNode 执行"""
    
    def test_execute_success_first_try(self, sample_df, mock_llm_client, mock_executor):
        """测试首次执行即成功"""
        # Mock LLM 客户端
        mock_client_instance = MagicMock()
        mock_llm_client.return_value = mock_client_instance
        
        # Mock generate 方法返回的响应对象
        mock_response = MagicMock()
        mock_response.content = "<think>\n思考过程\n</think>\n<packages>\n[]\n</packages>\n<code>\nresult = df[df['age'] > 30]\n</code>"
        mock_client_instance.generate.return_value = mock_response
        
        # Mock Executor
        mock_executor_instance = MagicMock()
        mock_executor.return_value = mock_executor_instance
        filtered_df = sample_df[sample_df['age'] > 30]
        mock_executor_instance.execute.return_value = (True, filtered_df, None)
        
        # 创建节点
        node = DataCoderNode(config={"api_key": "test-key"})
        
        # 准备输入（使用正确的格式）
        inputs = {
            "data": NodeInput(data={"dataframe": sample_df}),
            "task": NodeInput(data={"description": "过滤出年龄大于30的记录"})
        }
        
        # 执行节点
        outputs = node.run(inputs)
        
        # 验证结果
        assert "result" in outputs
        result_output = outputs["result"]
        assert result_output.status == NodeStatus.SUCCESS
        assert "dataframe" in result_output.data
        assert len(result_output.data["dataframe"]) == 3  # age > 30: Charlie(35), David(40), Eve(45)
        assert result_output.metrics["retries"] == 0
        assert result_output.metadata["code"] == "result = df[df['age'] > 30]"
    
    def test_execute_success_after_retry(self, sample_df, mock_llm_client, mock_executor):
        """测试经过重试后成功"""
        # Mock LLM 客户端
        mock_client_instance = MagicMock()
        mock_llm_client.return_value = mock_client_instance
        
        # 第一次生成错误代码
        mock_response_1 = MagicMock()
        mock_response_1.content = "<think>\n思考过程\n</think>\n<packages>\n[]\n</packages>\n<code>\nresult = df[df['age'] >> 30]\n</code>"
        
        # 第二次生成正确代码
        mock_response_2 = MagicMock()
        mock_response_2.content = "<think>\n修正后的思考\n</think>\n<packages>\n[]\n</packages>\n<code>\nresult = df[df['age'] > 30]\n</code>"
        
        mock_client_instance.generate.side_effect = [mock_response_1, mock_response_2]
        
        # Mock Executor
        mock_executor_instance = MagicMock()
        mock_executor.return_value = mock_executor_instance
        
        # 第一次失败，第二次成功
        filtered_df = sample_df[sample_df['age'] > 30]
        mock_executor_instance.execute.side_effect = [
            (False, None, "SyntaxError: invalid syntax"),
            (True, filtered_df, None)
        ]
        
        # 创建节点
        node = DataCoderNode(config={"api_key": "test-key", "verbose": False})
        
        # 准备输入（使用正确的格式）
        inputs = {
            "data": NodeInput(data={"dataframe": sample_df}),
            "task": NodeInput(data={"description": "过滤出年龄大于30的记录"})
        }
        
        # 执行节点
        outputs = node.run(inputs)
        
        # 验证结果
        result_output = outputs["result"]
        assert result_output.status == NodeStatus.SUCCESS
        assert "dataframe" in result_output.data
        assert len(result_output.data["dataframe"]) == 3  # age > 30: Charlie(35), David(40), Eve(45)
        assert result_output.metrics["retries"] == 1
        assert len(result_output.logs) >= 2  # 至少包含两次执行的日志
    
    def test_execute_failure_max_retries(self, sample_df, mock_llm_client, mock_executor):
        """测试达到最大重试次数后失败"""
        # Mock LLM 客户端
        mock_client_instance = MagicMock()
        mock_llm_client.return_value = mock_client_instance
        mock_client_instance.chat.return_value = "result = bad_code"
        
        mock_response = MagicMock()
        mock_response.content = "result = still_bad_code"
        mock_client_instance.generate.return_value = mock_response
        
        # Mock Executor - 一直失败
        mock_executor_instance = MagicMock()
        mock_executor.return_value = mock_executor_instance
        mock_executor_instance.execute.return_value = (False, None, "NameError: name 'bad_code' is not defined")
        
        # 创建节点
        node = DataCoderNode(config={"api_key": "test-key", "max_retries": 2, "verbose": False})
        
        # 准备输入（使用正确的格式）
        inputs = {
            "data": NodeInput(data={"dataframe": sample_df}),
            "task": NodeInput(data={"description": "执行某个任务"})
        }
        
        # 执行节点
        outputs = node.run(inputs)
        
        # 验证结果
        result_output = outputs["result"]
        assert result_output.status == NodeStatus.FAILED
        assert result_output.metrics["retries"] == 2
        assert "已重试 2 次" in result_output.error
        assert len(result_output.logs) >= 3  # 初始 + 2次重试
    
    def test_execute_invalid_input_type(self, mock_llm_client, mock_executor):
        """测试无效的输入类型"""
        # 创建节点
        node = DataCoderNode(config={"api_key": "test-key"})
        
        # 准备无效输入（使用正确的格式但数据类型错误）
        inputs = {
            "data": NodeInput(data={"dataframe": "not a dataframe"}),
            "task": NodeInput(data={"description": "做一些处理"})
        }
        
        # 执行节点
        outputs = node.run(inputs)
        
        # 验证结果
        result_output = outputs["result"]
        assert result_output.status == NodeStatus.FAILED
        assert "DataFrame" in result_output.error


class TestDataCoderNodeHelperMethods:
    """测试 DataCoderNode 辅助方法"""
    
    def test_get_dataframe_info(self, sample_df, mock_llm_client, mock_executor):
        """测试获取 DataFrame 信息"""
        node = DataCoderNode(config={"api_key": "test-key"})
        info = node._get_dataframe_info(sample_df)
        
        assert "形状: (5, 4)" in info
        assert "name: object" in info
        assert "age: int64" in info
        assert "前 5 行数据" in info
        assert "Alice" in info
    
    # Note: _clean_code 方法已经被移除或不再公开,代码清理逻辑已集成到其他方法中
    
    # Note: reset 和 cleanup 方法不再是 DataCoderNode 的公开 API
    # 节点状态管理已经通过基类的机制处理


class TestDataCoderNodeEdgeCases:
    """边界情况测试"""
    
    def test_empty_dataframe(self, mock_llm_client, mock_executor):
        """测试空 DataFrame"""
        empty_df = pd.DataFrame()
        
        mock_client_instance = MagicMock()
        mock_llm_client.return_value = mock_client_instance
        
        # Mock generate 方法
        mock_response = MagicMock()
        mock_response.content = "<think>\n返回原始数据\n</think>\n<packages>\n[]\n</packages>\n<code>\nresult = df\n</code>"
        mock_client_instance.generate.return_value = mock_response
        
        mock_executor_instance = MagicMock()
        mock_executor.return_value = mock_executor_instance
        mock_executor_instance.execute.return_value = (True, empty_df, None)
        
        node = DataCoderNode(config={"api_key": "test-key"})
        
        inputs = {
            "data": NodeInput(data={"dataframe": empty_df}),
            "task": NodeInput(data={"description": "返回原始数据"})
        }
        
        outputs = node.run(inputs)
        result_output = outputs["result"]
        
        assert result_output.status == NodeStatus.SUCCESS
        assert "dataframe" in result_output.data
        assert len(result_output.data["dataframe"]) == 0
    
    def test_large_dataframe_info(self, mock_llm_client, mock_executor):
        """测试大型 DataFrame 的信息提取"""
        large_df = pd.DataFrame({
            f'col_{i}': range(1000) for i in range(50)
        })
        
        node = DataCoderNode(config={"api_key": "test-key"})
        info = node._get_dataframe_info(large_df)
        
        assert "形状: (1000, 50)" in info
        assert "前 5 行数据" in info
    
    def test_dataframe_with_nulls(self, mock_llm_client, mock_executor):
        """测试包含空值的 DataFrame"""
        df_with_nulls = pd.DataFrame({
            'a': [1, 2, None, 4],
            'b': [None, 'x', 'y', 'z']
        })
        
        node = DataCoderNode(config={"api_key": "test-key"})
        info = node._get_dataframe_info(df_with_nulls)
        
        assert "空值" in info


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v", "-s"])
