"""NodeExecutor 单元测试"""

import pytest
from deepeye.nodes import BaseNode, NodeInput, NodeOutput, NodeInputPort, NodeOutputPort
from deepeye.runtime import ExecutionContext, NodeExecutor, ExecutionStatus
from deepeye.workflow import Workflow, NodeConnection
from deepeye.exceptions import NodeExecutionError


# ========== 测试辅助节点 ==========

class DummyNode(BaseNode):
    """测试用虚拟节点"""
    
    node_type = "Dummy"
    
    def __init__(self, node_id=None, should_fail=False):
        super().__init__(node_id)
        self.should_fail = should_fail
        self.input_ports = [
            NodeInputPort(name="data", label="数据输入", required=True)
        ]
        self.output_ports = [
            NodeOutputPort(name="output", label="输出")
        ]
    
    def execute(self, inputs):
        if self.should_fail:
            raise ValueError("节点配置为失败")
        
        input_data = self.get_single_input(inputs)
        value = input_data.get("value", 0)
        
        return self.create_single_output(data={"value": value * 2})


class SourceNode(BaseNode):
    """数据源节点（无输入）"""
    
    node_type = "Source"
    
    def __init__(self, node_id=None, value=42):
        super().__init__(node_id)
        self.value = value
        self.input_ports = []  # 无输入
        self.output_ports = [
            NodeOutputPort(name="data", label="数据输出")
        ]
    
    def execute(self, inputs):
        return {"data": NodeOutput(data={"value": self.value})}


class MultiInputNode(BaseNode):
    """多输入节点"""
    
    node_type = "MultiInput"
    
    def __init__(self, node_id=None):
        super().__init__(node_id)
        self.input_ports = [
            NodeInputPort(name="input1", label="输入1", required=True),
            NodeInputPort(name="input2", label="输入2", required=True),
        ]
        self.output_ports = [
            NodeOutputPort(name="output", label="输出")
        ]
    
    def execute(self, inputs):
        value1 = inputs["input1"].get("value", 0)
        value2 = inputs["input2"].get("value", 0)
        
        return self.create_single_output(data={"value": value1 + value2})


# ========== 测试类 ==========

class TestNodeExecutor:
    """NodeExecutor 测试"""
    
    def test_init(self):
        """测试初始化"""
        context = ExecutionContext(workflow_id="wf1", execution_id="exec1")
        executor = NodeExecutor(context)
        
        assert executor.context == context
    
    def test_prepare_inputs_no_predecessors(self):
        """测试准备输入 - 没有前驱节点"""
        # 创建工作流和节点
        workflow = Workflow(name="test", workflow_id="test")
        source = SourceNode(node_id="source")
        workflow.add_node("source", source)
        
        # 创建执行器
        context = ExecutionContext(workflow_id="test", execution_id="exec1")
        executor = NodeExecutor(context)
        
        # 准备输入（没有前驱节点）
        inputs = executor.prepare_inputs("source", source, workflow)
        
        # 应该返回空字典
        assert inputs == {}
    
    def test_prepare_inputs_single_predecessor(self):
        """测试准备输入 - 单个前驱节点"""
        # 创建工作流
        workflow = Workflow(name="test", workflow_id="test")
        
        # 添加节点
        source = SourceNode(node_id="source")
        process = DummyNode(node_id="process")
        
        workflow.add_node("source", source)
        workflow.add_node("process", process)
        
        # 添加连接: source.data -> process.data
        workflow.add_connection("source", "process", "data", "data")
        
        # 创建执行器并设置前驱节点的输出
        context = ExecutionContext(workflow_id="test", execution_id="exec1")
        context.set_node_outputs("source", {
            "data": NodeOutput(data={"value": 100})
        })
        
        executor = NodeExecutor(context)
        
        # 准备输入
        inputs = executor.prepare_inputs("process", process, workflow)
        
        # 验证
        assert "data" in inputs
        assert isinstance(inputs["data"], NodeInput)
        assert inputs["data"].get("value") == 100
        assert inputs["data"].metadata["from_node"] == "source"
        assert inputs["data"].metadata["from_port"] == "data"
    
    def test_prepare_inputs_multiple_predecessors(self):
        """测试准备输入 - 多个前驱节点"""
        # 创建工作流
        workflow = Workflow(name="test", workflow_id="test")
        
        # 添加节点
        source1 = SourceNode(node_id="source1", value=10)
        source2 = SourceNode(node_id="source2", value=20)
        merge = MultiInputNode(node_id="merge")
        
        workflow.add_node("source1", source1)
        workflow.add_node("source2", source2)
        workflow.add_node("merge", merge)
        
        # 添加连接
        workflow.add_connection("source1", "merge", "data", "input1")
        workflow.add_connection("source2", "merge", "data", "input2")
        
        # 创建执行器并设置前驱节点的输出
        context = ExecutionContext(workflow_id="test", execution_id="exec1")
        context.set_node_outputs("source1", {
            "data": NodeOutput(data={"value": 10})
        })
        context.set_node_outputs("source2", {
            "data": NodeOutput(data={"value": 20})
        })
        
        executor = NodeExecutor(context)
        
        # 准备输入
        inputs = executor.prepare_inputs("merge", merge, workflow)
        
        # 验证
        assert "input1" in inputs
        assert "input2" in inputs
        assert inputs["input1"].get("value") == 10
        assert inputs["input2"].get("value") == 20
    
    def test_prepare_inputs_missing_predecessor_output(self):
        """测试准备输入 - 前驱节点输出缺失"""
        # 创建工作流
        workflow = Workflow(name="test", workflow_id="test")
        
        source = SourceNode(node_id="source")
        process = DummyNode(node_id="process")
        
        workflow.add_node("source", source)
        workflow.add_node("process", process)
        workflow.add_connection("source", "process", "data", "data")
        
        # 创建执行器（不设置前驱节点输出）
        context = ExecutionContext(workflow_id="test", execution_id="exec1")
        executor = NodeExecutor(context)
        
        # 准备输入应该失败
        with pytest.raises(NodeExecutionError) as exc_info:
            executor.prepare_inputs("process", process, workflow)
        
        assert "尚未执行" in str(exc_info.value)
    
    def test_prepare_inputs_invalid_output_port(self):
        """测试准备输入 - 无效的输出端口"""
        # 创建工作流
        workflow = Workflow(name="test", workflow_id="test")
        
        source = SourceNode(node_id="source")
        process = DummyNode(node_id="process")
        
        workflow.add_node("source", source)
        workflow.add_node("process", process)
        
        # 连接到不存在的端口
        workflow.add_connection("source", "process", "invalid_port", "data")
        
        # 创建执行器并设置输出（但没有 invalid_port）
        context = ExecutionContext(workflow_id="test", execution_id="exec1")
        context.set_node_outputs("source", {
            "data": NodeOutput(data={"value": 100})
        })
        
        executor = NodeExecutor(context)
        
        # 准备输入应该失败
        with pytest.raises(NodeExecutionError) as exc_info:
            executor.prepare_inputs("process", process, workflow)
        
        assert "没有输出端口" in str(exc_info.value)
    
    def test_execute_with_provided_inputs_success(self):
        """测试使用提供输入执行节点 - 成功"""
        # 创建节点和执行器
        node = DummyNode(node_id="node1")
        context = ExecutionContext(workflow_id="test", execution_id="exec1")
        executor = NodeExecutor(context)
        
        # 提供输入
        inputs = {
            "data": NodeInput(data={"value": 5})
        }
        
        # 执行节点
        result = executor.execute_with_provided_inputs("node1", node, inputs)
        
        # 验证结果
        assert result.node_id == "node1"
        assert result.status == ExecutionStatus.SUCCESS
        assert result.outputs is not None
        assert "output" in result.outputs
        assert result.outputs["output"].data["value"] == 10  # 5 * 2
        assert result.error is None
        
        # 验证输出已保存到上下文
        saved_outputs = context.get_node_outputs("node1")
        assert saved_outputs is not None
        assert saved_outputs["output"].data["value"] == 10
    
    def test_execute_with_provided_inputs_failure(self):
        """测试使用提供输入执行节点 - 失败"""
        # 创建会失败的节点
        node = DummyNode(node_id="node1", should_fail=True)
        context = ExecutionContext(workflow_id="test", execution_id="exec1")
        executor = NodeExecutor(context)
        
        # 提供输入
        inputs = {
            "data": NodeInput(data={"value": 5})
        }
        
        # 执行节点
        result = executor.execute_with_provided_inputs("node1", node, inputs)
        
        # 验证结果
        assert result.node_id == "node1"
        assert result.status == ExecutionStatus.FAILED
        assert result.outputs is None
        assert result.error is not None
        assert "节点配置为失败" in str(result.error)
    
    def test_execute_node_success(self):
        """测试执行节点 - 成功"""
        # 创建工作流
        workflow = Workflow(name="test", workflow_id="test")
        
        source = SourceNode(node_id="source", value=7)
        process = DummyNode(node_id="process")
        
        workflow.add_node("source", source)
        workflow.add_node("process", process)
        workflow.add_connection("source", "process", "data", "data")
        
        # 创建执行器
        context = ExecutionContext(workflow_id="test", execution_id="exec1")
        executor = NodeExecutor(context)
        
        # 先执行源节点
        source_result = executor.execute_with_provided_inputs("source", source, {})
        assert source_result.status == ExecutionStatus.SUCCESS
        
        # 然后执行处理节点
        process_result = executor.execute_node("process", process, workflow)
        
        # 验证结果
        assert process_result.status == ExecutionStatus.SUCCESS
        assert process_result.outputs["output"].data["value"] == 14  # 7 * 2
        
        # 验证上下文中有两个节点的输出
        assert context.get_node_outputs("source") is not None
        assert context.get_node_outputs("process") is not None
    
    def test_execute_node_with_missing_input(self):
        """测试执行节点 - 缺少输入"""
        # 创建工作流
        workflow = Workflow(name="test", workflow_id="test")
        
        source = SourceNode(node_id="source")
        process = DummyNode(node_id="process")
        
        workflow.add_node("source", source)
        workflow.add_node("process", process)
        workflow.add_connection("source", "process", "data", "data")
        
        # 创建执行器（不执行源节点）
        context = ExecutionContext(workflow_id="test", execution_id="exec1")
        executor = NodeExecutor(context)
        
        # 尝试执行处理节点（输入缺失）
        result = executor.execute_node("process", process, workflow)
        
        # 应该失败
        assert result.status == ExecutionStatus.FAILED
        assert "尚未执行" in str(result.error)
    
    def test_execute_node_execution_failure(self):
        """测试执行节点 - 执行过程中失败"""
        # 创建工作流
        workflow = Workflow(name="test", workflow_id="test")
        
        source = SourceNode(node_id="source", value=5)
        process = DummyNode(node_id="process", should_fail=True)
        
        workflow.add_node("source", source)
        workflow.add_node("process", process)
        workflow.add_connection("source", "process", "data", "data")
        
        # 创建执行器
        context = ExecutionContext(workflow_id="test", execution_id="exec1")
        executor = NodeExecutor(context)
        
        # 执行源节点
        executor.execute_with_provided_inputs("source", source, {})
        
        # 执行处理节点（会失败）
        result = executor.execute_node("process", process, workflow)
        
        # 验证结果
        assert result.status == ExecutionStatus.FAILED
        assert "节点配置为失败" in str(result.error)
        assert result.outputs is None
        
        # 源节点的输出应该在上下文中
        assert context.get_node_outputs("source") is not None
        # 处理节点不应该有输出
        assert context.get_node_outputs("process") is None


class TestNodeExecutorIntegration:
    """NodeExecutor 集成测试"""
    
    def test_linear_workflow_execution(self):
        """测试线性工作流执行"""
        # 创建线性工作流: source -> node1 -> node2
        workflow = Workflow(name="linear", workflow_id="linear")
        
        source = SourceNode(node_id="source", value=3)
        node1 = DummyNode(node_id="node1")
        node2 = DummyNode(node_id="node2")
        
        workflow.add_node("source", source)
        workflow.add_node("node1", node1)
        workflow.add_node("node2", node2)
        
        workflow.add_connection("source", "node1", "data", "data")
        workflow.add_connection("node1", "node2", "output", "data")
        
        # 创建执行器
        context = ExecutionContext(workflow_id="linear", execution_id="exec1")
        executor = NodeExecutor(context)
        
        # 按顺序执行
        r1 = executor.execute_with_provided_inputs("source", source, {})
        r2 = executor.execute_node("node1", node1, workflow)
        r3 = executor.execute_node("node2", node2, workflow)
        
        # 验证
        assert r1.status == ExecutionStatus.SUCCESS
        assert r2.status == ExecutionStatus.SUCCESS
        assert r3.status == ExecutionStatus.SUCCESS
        
        # 验证数据流: 3 -> 6 -> 12
        assert context.get_node_output("source", "data").data["value"] == 3
        assert context.get_node_output("node1", "output").data["value"] == 6
        assert context.get_node_output("node2", "output").data["value"] == 12

