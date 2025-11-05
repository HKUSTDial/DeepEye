"""WorkflowExecutor 单元测试"""

import pytest
from deepeye.nodes import BaseNode, NodeInput, NodeOutput, NodeInputPort, NodeOutputPort
from deepeye.runtime import WorkflowExecutor, ExecutionStatus
from deepeye.workflow import Workflow
from deepeye.exceptions import WorkflowExecutionError


# ========== 测试辅助节点 ==========

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


class ProcessNode(BaseNode):
    """处理节点（单输入单输出）"""
    
    node_type = "Process"
    
    def __init__(self, node_id=None, multiplier=2):
        super().__init__(node_id)
        self.multiplier = multiplier
        self.input_ports = [
            NodeInputPort(name="data", label="数据输入", required=True)
        ]
        self.output_ports = [
            NodeOutputPort(name="result", label="结果输出")
        ]
    
    def execute(self, inputs):
        input_data = self.get_single_input(inputs)
        value = input_data.get("value", 0)
        
        return {"result": NodeOutput(data={"value": value * self.multiplier})}


class FailNode(BaseNode):
    """会失败的节点"""
    
    node_type = "Fail"
    
    def __init__(self, node_id=None):
        super().__init__(node_id)
        self.input_ports = [
            NodeInputPort(name="data", label="数据输入", required=True)
        ]
        self.output_ports = [
            NodeOutputPort(name="result", label="结果输出")
        ]
    
    def execute(self, inputs):
        raise ValueError("这个节点被配置为失败")


class MergeNode(BaseNode):
    """合并节点（多输入单输出）"""
    
    node_type = "Merge"
    
    def __init__(self, node_id=None):
        super().__init__(node_id)
        self.input_ports = [
            NodeInputPort(name="input1", label="输入1", required=True),
            NodeInputPort(name="input2", label="输入2", required=True),
        ]
        self.output_ports = [
            NodeOutputPort(name="merged", label="合并输出")
        ]
    
    def execute(self, inputs):
        value1 = inputs["input1"].get("value", 0)
        value2 = inputs["input2"].get("value", 0)
        
        return {"merged": NodeOutput(data={"value": value1 + value2})}


# ========== 测试类 ==========

class TestWorkflowExecutor:
    """WorkflowExecutor 测试"""
    
    def test_init(self):
        """测试初始化"""
        workflow = Workflow(name="test", workflow_id="test")
        executor = WorkflowExecutor(workflow)
        
        assert executor.workflow == workflow
        assert executor.context is not None
        assert executor.node_executor is not None
        assert executor.fail_fast is True
    
    def test_init_with_custom_execution_id(self):
        """测试使用自定义执行 ID 初始化"""
        workflow = Workflow(name="test", workflow_id="test")
        executor = WorkflowExecutor(workflow, execution_id="custom-exec-123")
        
        assert executor.context.execution_id == "custom-exec-123"
    
    def test_execute_empty_workflow(self):
        """测试执行空工作流"""
        workflow = Workflow(name="empty", workflow_id="empty")
        executor = WorkflowExecutor(workflow)
        
        # 空工作流应该成功执行（没有节点）
        result = executor.execute()
        
        assert result.status == ExecutionStatus.SUCCESS
        assert len(result.node_results) == 0
    
    def test_execute_single_node_workflow(self):
        """测试执行单节点工作流"""
        # 创建工作流
        workflow = Workflow(name="single", workflow_id="single")
        source = SourceNode(node_id="source", value=100)
        workflow.add_node("source", source)
        
        # 执行
        executor = WorkflowExecutor(workflow)
        result = executor.execute()
        
        # 验证
        assert result.status == ExecutionStatus.SUCCESS
        assert len(result.node_results) == 1
        
        source_result = result.get_node_result("source")
        assert source_result.status == ExecutionStatus.SUCCESS
        assert source_result.outputs["data"].data["value"] == 100
    
    def test_execute_linear_workflow(self):
        """测试执行线性工作流"""
        # 创建线性工作流: source -> process1 -> process2
        workflow = Workflow(name="linear", workflow_id="linear")
        
        source = SourceNode(node_id="source", value=5)
        process1 = ProcessNode(node_id="process1", multiplier=2)
        process2 = ProcessNode(node_id="process2", multiplier=3)
        
        workflow.add_node("source", source)
        workflow.add_node("process1", process1)
        workflow.add_node("process2", process2)
        
        workflow.add_connection("source", "process1", "data", "data")
        workflow.add_connection("process1", "process2", "result", "data")
        
        # 执行
        executor = WorkflowExecutor(workflow)
        result = executor.execute()
        
        # 验证
        assert result.status == ExecutionStatus.SUCCESS
        assert len(result.node_results) == 3
        
        # 验证数据流: 5 -> 10 -> 30
        assert result.get_node_result("source").outputs["data"].data["value"] == 5
        assert result.get_node_result("process1").outputs["result"].data["value"] == 10
        assert result.get_node_result("process2").outputs["result"].data["value"] == 30
    
    def test_execute_with_external_inputs(self):
        """测试使用外部输入执行"""
        # 创建工作流: source (外部输入) -> process
        workflow = Workflow(name="with_input", workflow_id="with_input")
        
        source = SourceNode(node_id="source", value=1)  # 默认值
        process = ProcessNode(node_id="process", multiplier=5)
        
        workflow.add_node("source", source)
        workflow.add_node("process", process)
        workflow.add_connection("source", "process", "data", "data")
        
        # 执行（不提供外部输入，使用source的默认值）
        executor = WorkflowExecutor(workflow)
        result = executor.execute()
        
        # 验证
        assert result.status == ExecutionStatus.SUCCESS
        # source 默认值 1, process: 1 * 5 = 5
        assert result.get_node_result("process").outputs["result"].data["value"] == 5
    
    def test_execute_branching_workflow(self):
        """测试执行分支工作流"""
        # 创建分支工作流: source -> process1, process2 -> merge
        workflow = Workflow(name="branch", workflow_id="branch")
        
        source = SourceNode(node_id="source", value=10)
        process1 = ProcessNode(node_id="process1", multiplier=2)
        process2 = ProcessNode(node_id="process2", multiplier=3)
        merge = MergeNode(node_id="merge")
        
        workflow.add_node("source", source)
        workflow.add_node("process1", process1)
        workflow.add_node("process2", process2)
        workflow.add_node("merge", merge)
        
        workflow.add_connection("source", "process1", "data", "data")
        workflow.add_connection("source", "process2", "data", "data")
        workflow.add_connection("process1", "merge", "result", "input1")
        workflow.add_connection("process2", "merge", "result", "input2")
        
        # 执行
        executor = WorkflowExecutor(workflow)
        result = executor.execute()
        
        # 验证
        assert result.status == ExecutionStatus.SUCCESS
        assert len(result.node_results) == 4
        
        # 验证数据流: 10 -> (20, 30) -> 50
        assert result.get_node_result("process1").outputs["result"].data["value"] == 20
        assert result.get_node_result("process2").outputs["result"].data["value"] == 30
        assert result.get_node_result("merge").outputs["merged"].data["value"] == 50
    
    def test_execute_with_node_failure_fail_fast(self):
        """测试节点失败时快速失败"""
        # 创建工作流: source -> fail -> process
        workflow = Workflow(name="fail", workflow_id="fail")
        
        source = SourceNode(node_id="source", value=10)
        fail_node = FailNode(node_id="fail")
        process = ProcessNode(node_id="process", multiplier=2)
        
        workflow.add_node("source", source)
        workflow.add_node("fail", fail_node)
        workflow.add_node("process", process)
        
        workflow.add_connection("source", "fail", "data", "data")
        workflow.add_connection("fail", "process", "result", "data")
        
        # 执行（fail_fast=True）
        executor = WorkflowExecutor(workflow, fail_fast=True)
        result = executor.execute()
        
        # 验证
        assert result.status == ExecutionStatus.FAILED
        assert result.has_failed_nodes()
        
        # source 应该成功
        assert result.get_node_result("source").status == ExecutionStatus.SUCCESS
        
        # fail 应该失败
        assert result.get_node_result("fail").status == ExecutionStatus.FAILED
        
        # process 应该被跳过
        assert result.get_node_result("process").status == ExecutionStatus.SKIPPED
    
    def test_execute_with_node_failure_no_fail_fast(self):
        """测试节点失败时不快速失败"""
        # 创建工作流: source -> fail -> process
        workflow = Workflow(name="fail", workflow_id="fail")
        
        source = SourceNode(node_id="source", value=10)
        fail_node = FailNode(node_id="fail")
        process = ProcessNode(node_id="process", multiplier=2)
        
        workflow.add_node("source", source)
        workflow.add_node("fail", fail_node)
        workflow.add_node("process", process)
        
        workflow.add_connection("source", "fail", "data", "data")
        workflow.add_connection("fail", "process", "result", "data")
        
        # 执行（fail_fast=False）
        executor = WorkflowExecutor(workflow, fail_fast=False)
        result = executor.execute()
        
        # 验证
        assert result.status == ExecutionStatus.FAILED
        assert result.has_failed_nodes()
        
        # source 应该成功
        assert result.get_node_result("source").status == ExecutionStatus.SUCCESS
        
        # fail 应该失败
        assert result.get_node_result("fail").status == ExecutionStatus.FAILED
        
        # process 也会尝试执行，但因为缺少输入而失败
        assert result.get_node_result("process").status == ExecutionStatus.FAILED
    
    def test_execute_with_invalid_workflow(self):
        """测试执行无效工作流"""
        # 创建有循环的工作流
        workflow = Workflow(name="invalid", workflow_id="invalid")
        
        node1 = ProcessNode(node_id="node1")
        node2 = ProcessNode(node_id="node2")
        
        workflow.add_node("node1", node1)
        workflow.add_node("node2", node2)
        
        # 创建循环
        workflow.add_connection("node1", "node2", "result", "data")
        # 手动添加反向连接（绕过验证）
        from deepeye.workflow.graph import NodeConnection
        workflow.graph._graph.add_edge(
            "node2", "node1",
            connection=NodeConnection("node2", "result", "node1", "data")
        )
        
        # 执行应该失败
        executor = WorkflowExecutor(workflow)
        
        with pytest.raises(WorkflowExecutionError) as exc_info:
            executor.execute()
        
        assert "验证失败" in str(exc_info.value)
    
    def test_get_execution_layers(self):
        """测试获取执行层级"""
        # 创建多层工作流
        workflow = Workflow(name="layers", workflow_id="layers")
        
        source = SourceNode(node_id="source", value=1)
        p1 = ProcessNode(node_id="p1")
        p2 = ProcessNode(node_id="p2")
        p3 = ProcessNode(node_id="p3")
        
        workflow.add_node("source", source)
        workflow.add_node("p1", p1)
        workflow.add_node("p2", p2)
        workflow.add_node("p3", p3)
        
        workflow.add_connection("source", "p1", "data", "data")
        workflow.add_connection("source", "p2", "data", "data")
        workflow.add_connection("p1", "p3", "result", "data")
        
        # 获取层级
        executor = WorkflowExecutor(workflow)
        layers = executor.get_execution_layers()
        
        # 验证
        assert len(layers) == 3
        assert set(layers[0]) == {"source"}
        assert set(layers[1]) == {"p1", "p2"}
        assert set(layers[2]) == {"p3"}
    
    def test_execute_parallel_not_implemented(self):
        """测试并行执行（未实现）"""
        workflow = Workflow(name="test", workflow_id="test")
        executor = WorkflowExecutor(workflow)
        
        with pytest.raises(NotImplementedError) as exc_info:
            executor.execute_parallel()
        
        assert "Phase 4" in str(exc_info.value)


class TestWorkflowExecutorIntegration:
    """WorkflowExecutor 集成测试"""
    
    def test_complex_workflow_execution(self):
        """测试复杂工作流执行"""
        # 创建复杂工作流
        # source1, source2 -> process1, process2 -> merge -> final
        workflow = Workflow(name="complex", workflow_id="complex")
        
        source1 = SourceNode(node_id="source1", value=10)
        source2 = SourceNode(node_id="source2", value=20)
        process1 = ProcessNode(node_id="process1", multiplier=2)
        process2 = ProcessNode(node_id="process2", multiplier=3)
        merge = MergeNode(node_id="merge")
        final = ProcessNode(node_id="final", multiplier=5)
        
        workflow.add_node("source1", source1)
        workflow.add_node("source2", source2)
        workflow.add_node("process1", process1)
        workflow.add_node("process2", process2)
        workflow.add_node("merge", merge)
        workflow.add_node("final", final)
        
        workflow.add_connection("source1", "process1", "data", "data")
        workflow.add_connection("source2", "process2", "data", "data")
        workflow.add_connection("process1", "merge", "result", "input1")
        workflow.add_connection("process2", "merge", "result", "input2")
        workflow.add_connection("merge", "final", "merged", "data")
        
        # 执行
        executor = WorkflowExecutor(workflow)
        result = executor.execute()
        
        # 验证
        assert result.status == ExecutionStatus.SUCCESS
        assert result.is_success()
        assert len(result.node_results) == 6
        
        # 验证数据流
        # source1: 10, source2: 20
        # process1: 10*2=20, process2: 20*3=60
        # merge: 20+60=80
        # final: 80*5=400
        assert result.get_node_result("final").outputs["result"].data["value"] == 400
        
        # 验证统计信息
        stats = result.get_statistics()
        assert stats["total_nodes"] == 6
        assert stats["successful"] == 6
        assert stats["failed"] == 0
        assert stats["skipped"] == 0
    
    def test_workflow_execution_with_mixed_results(self):
        """测试包含成功和失败的工作流执行"""
        # 创建工作流：两个独立分支，一个成功一个失败
        workflow = Workflow(name="mixed", workflow_id="mixed")
        
        source1 = SourceNode(node_id="source1", value=10)
        source2 = SourceNode(node_id="source2", value=20)
        process1 = ProcessNode(node_id="process1")
        fail = FailNode(node_id="fail")
        
        workflow.add_node("source1", source1)
        workflow.add_node("source2", source2)
        workflow.add_node("process1", process1)
        workflow.add_node("fail", fail)
        
        workflow.add_connection("source1", "process1", "data", "data")
        workflow.add_connection("source2", "fail", "data", "data")
        
        # 执行（不快速失败）
        executor = WorkflowExecutor(workflow, fail_fast=False)
        result = executor.execute()
        
        # 验证
        assert result.status == ExecutionStatus.FAILED
        assert result.has_failed_nodes()
        
        # 成功的节点
        successful = result.get_successful_nodes()
        assert set(successful) == {"source1", "source2", "process1"}
        
        # 失败的节点
        failed = result.get_failed_nodes()
        assert set(failed) == {"fail"}

