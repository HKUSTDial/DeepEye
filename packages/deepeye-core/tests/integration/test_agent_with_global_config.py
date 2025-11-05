"""集成测试：Agent + GlobalConfig

测试 GlobalConfig 在 Agentic 编排模式下的集成。
"""

import pytest
import pandas as pd
from unittest.mock import Mock, patch

from deepeye.config import get_global_config
from deepeye.agent import PlannerAgent
from deepeye.nodes.datasource import MemoryDataSourceNode
from deepeye.nodes.processing import TransformNode
from deepeye.runtime import WorkflowExecutor, ExecutionContext
from deepeye.runtime.result import ExecutionStatus


class TestAgentWithGlobalConfig:
    """测试 Agent 与 GlobalConfig 的集成"""
    
    def setup_method(self):
        """每个测试前清空 GlobalConfig"""
        config = get_global_config()
        config.clear_all()
    
    def test_workflow_executor_accepts_context(self):
        """测试 WorkflowExecutor 能够接受 ExecutionContext"""
        from deepeye.workflow import Workflow
        
        # 创建工作流
        workflow = Workflow(name="test")
        
        # 创建 ExecutionContext
        context = ExecutionContext(workflow_id="test_wf")
        context.set_variable("test_key", "test_value")
        
        # 创建 WorkflowExecutor，传入 context
        executor = WorkflowExecutor(workflow, context=context)
        
        # 验证 context 被正确设置
        assert executor.context is context
        assert executor.context.get_variable("test_key") == "test_value"
    
    def test_workflow_executor_creates_new_context_if_not_provided(self):
        """测试 WorkflowExecutor 在未提供 context 时创建新的"""
        from deepeye.workflow import Workflow
        
        workflow = Workflow(name="test")
        executor = WorkflowExecutor(workflow)
        
        # 验证创建了新的 context
        assert executor.context is not None
        assert executor.context.workflow_id == workflow.workflow_id
    
    def test_global_config_integration_with_memory_node(self):
        """测试 GlobalConfig 与 MemoryDataSource 的集成"""
        # 配置 GlobalConfig
        config = get_global_config()
        test_df = pd.DataFrame({
            "col1": [1, 2, 3],
            "col2": ["a", "b", "c"]
        })
        config.set_node_config("MemoryDataSource", {
            "data": test_df,  # MemoryDataSourceConfig 的字段名是 data
        })
        
        # 创建节点（不传递 config）
        node = MemoryDataSourceNode(node_id="test_memory")
        
        # 验证节点的配置来自 GlobalConfig
        pd.testing.assert_frame_equal(node.config.data, test_df)
    
    def test_execution_context_preserves_static_inputs(self):
        """测试 ExecutionContext 能够保存和检索静态输入"""
        context = ExecutionContext(workflow_id="test")
        
        # 设置静态输入
        context.set_node_input("node1", "port1", {"key": "value"})
        
        # 检索静态输入
        retrieved = context.get_node_input("node1", "port1")
        assert retrieved == {"key": "value"}
        
        # 检查是否存在
        assert context.has_node_input("node1", "port1")
        assert not context.has_node_input("node1", "port2")
    
    def test_context_with_workflow_executor_integration(self):
        """测试 ExecutionContext 与 WorkflowExecutor 的完整集成"""
        from deepeye.workflow import Workflow
        from deepeye.nodes.io import NodeInput
        
        # 创建简单工作流
        workflow = Workflow(name="test_integration")
        
        # 添加一个内存数据源节点
        test_df = pd.DataFrame({
            "x": [1, 2, 3],
            "y": [4, 5, 6]
        })
        
        # 通过 GlobalConfig 配置节点
        config = get_global_config()
        config.set_node_config("MemoryDataSource", {
            "data": test_df,  # 注意：MemoryDataSourceConfig 的字段名是 data，不是 dataframe
        })
        
        # 创建节点（会从 GlobalConfig 读取配置）
        node = MemoryDataSourceNode(node_id="data_source")
        workflow.add_node("data_source", node)
        
        # 创建 ExecutionContext（Agent 模式下会用到）
        context = ExecutionContext(workflow_id=workflow.workflow_id)
        
        # 创建执行器并执行
        executor = WorkflowExecutor(workflow, context=context)
        result = executor.execute()
        
        # 验证执行成功
        assert result.is_success()
        assert "data_source" in result.node_results
        
        # 验证输出数据正确
        node_result = result.node_results["data_source"]
        assert node_result.status == ExecutionStatus.SUCCESS
        assert node_result.outputs is not None
        assert "data" in node_result.outputs  # 输出端口名是 data
        output_df = node_result.outputs["data"].data["dataframe"]
        pd.testing.assert_frame_equal(output_df, test_df)
    
    @pytest.mark.skip(reason="需要 LLM API，跳过")
    def test_agent_with_global_config_full_flow(self):
        """测试完整的 Agent + GlobalConfig 流程（需要真实的 LLM API）"""
        # 这个测试需要真实的 LLM API，通常在 CI 中跳过
        # 可以在本地手动运行以验证完整流程
        pass


class TestAgentGlobalConfigEdgeCases:
    """测试边界情况"""
    
    def setup_method(self):
        """每个测试前清空 GlobalConfig"""
        config = get_global_config()
        config.clear_all()
    
    def test_partial_config_override(self):
        """测试部分配置覆盖"""
        config = get_global_config()
        
        # 设置全局配置
        test_df = pd.DataFrame({"a": [1, 2]})
        test_columns = ["a"]
        config.set_node_config("MemoryDataSource", {
            "data": test_df,
            "columns": test_columns
        })
        
        # 创建节点时部分覆盖
        override_df = pd.DataFrame({"b": [3, 4]})
        node = MemoryDataSourceNode(
            node_id="test",
            config={"data": override_df}  # 只覆盖 data，columns 保持全局配置
        )
        
        # 验证覆盖生效
        pd.testing.assert_frame_equal(node.config.data, override_df)
        # 验证未覆盖的参数使用全局配置
        assert node.config.columns == test_columns
    
    def test_no_global_config_uses_default(self):
        """测试没有全局配置时使用节点默认值"""
        config = get_global_config()
        config.clear_all()
        
        # 创建节点（没有全局配置，也没有传递 config）
        # 应该使用节点的默认值
        node = MemoryDataSourceNode(node_id="test")
        
        # 验证使用了默认值（MemoryDataSourceConfig 只有 data 和 columns 字段）
        assert node.config.data is None
        assert node.config.columns is None
    
    def test_context_workflow_id_sync(self):
        """测试 WorkflowExecutor 同步 workflow_id"""
        from deepeye.workflow import Workflow
        
        workflow = Workflow(name="test", workflow_id="workflow_123")
        context = ExecutionContext(workflow_id="different_id")
        
        # 创建执行器时应该同步 workflow_id
        executor = WorkflowExecutor(workflow, context=context)
        
        # 验证 workflow_id 已同步
        assert executor.context.workflow_id == "workflow_123"

