"""测试工作流验证器"""

import pytest
from deepeye.workflow.graph import WorkflowGraph, NodeConnection
from deepeye.workflow.validator import (
    WorkflowValidator,
    ValidationReport,
    ValidationIssue,
)
from deepeye.nodes import BaseNode, NodeOutput, NodeMetadata, NodeInputPort
from deepeye.exceptions import WorkflowValidationError


class DummyNode(BaseNode):
    """测试用虚拟节点"""
    
    node_type = "Dummy"
    
    def __init__(self, node_id=None, config=None, num_inputs=1, num_outputs=1):
        super().__init__(node_id, config)
        self.metadata = NodeMetadata(name="Dummy", display_name="虚拟节点")
        
        # 创建输入端口
        self.input_ports = [
            NodeInputPort(name=f"input{i}", label=f"输入{i}", required=True)
            for i in range(num_inputs)
        ]
        
        # 创建输出端口
        from deepeye.nodes.io import NodeOutputPort
        self.output_ports = [
            NodeOutputPort(name=f"output{i}", label=f"输出{i}")
            for i in range(num_outputs)
        ]
    
    def execute(self, inputs):
        # 为每个输出端口返回数据
        outputs = {}
        for port in self.output_ports:
            outputs[port.name] = NodeOutput(data={"result": "dummy"})
        return outputs


class TestValidationIssue:
    """测试验证问题"""
    
    def test_create_issue(self):
        """测试创建验证问题"""
        issue = ValidationIssue(
            level="error",
            message="测试错误",
            node_id="node1",
            details={"key": "value"}
        )
        
        assert issue.level == "error"
        assert issue.message == "测试错误"
        assert issue.node_id == "node1"
        assert issue.details == {"key": "value"}
    
    def test_issue_str(self):
        """测试验证问题字符串表示"""
        issue = ValidationIssue(
            level="error",
            message="测试错误",
            node_id="node1"
        )
        
        str_repr = str(issue)
        assert "ERROR" in str_repr
        assert "node1" in str_repr
        assert "测试错误" in str_repr


class TestValidationReport:
    """测试验证报告"""
    
    def test_create_empty_report(self):
        """测试创建空报告"""
        report = ValidationReport()
        
        assert report.is_valid
        assert len(report.errors) == 0
        assert len(report.warnings) == 0
        assert len(report.info) == 0
        assert not report.has_errors()
        assert not report.has_warnings()
    
    def test_add_error(self):
        """测试添加错误"""
        report = ValidationReport()
        report.add_error("测试错误", node_id="node1")
        
        assert not report.is_valid
        assert report.has_errors()
        assert len(report.errors) == 1
        assert report.errors[0].message == "测试错误"
        assert report.errors[0].node_id == "node1"
    
    def test_add_warning(self):
        """测试添加警告"""
        report = ValidationReport()
        report.add_warning("测试警告", node_id="node1")
        
        assert report.is_valid  # 警告不影响 is_valid
        assert report.has_warnings()
        assert len(report.warnings) == 1
    
    def test_add_info(self):
        """测试添加信息"""
        report = ValidationReport()
        report.add_info("测试信息")
        
        assert report.is_valid
        assert len(report.info) == 1
    
    def test_get_summary(self):
        """测试获取摘要"""
        report = ValidationReport()
        assert "验证通过" in report.get_summary()
        
        report.add_error("测试错误")
        assert "验证失败" in report.get_summary()
    
    def test_report_str(self):
        """测试报告字符串表示"""
        report = ValidationReport()
        report.add_error("错误1")
        report.add_warning("警告1")
        report.add_info("信息1")
        
        str_repr = str(report)
        assert "验证失败" in str_repr
        assert "错误1" in str_repr
        assert "警告1" in str_repr
        assert "信息1" in str_repr


class TestWorkflowValidator:
    """测试工作流验证器"""
    
    def test_create_validator(self):
        """测试创建验证器"""
        validator = WorkflowValidator()
        assert validator is not None
    
    def test_validate_empty_graph(self):
        """测试验证空图"""
        validator = WorkflowValidator()
        graph = WorkflowGraph()
        nodes = {}
        
        report = validator.validate(graph, nodes)
        
        assert report.is_valid
        assert report.has_warnings()
        assert any("为空" in w.message for w in report.warnings)
    
    def test_validate_simple_workflow(self):
        """测试验证简单工作流"""
        validator = WorkflowValidator()
        
        # 创建图
        graph = WorkflowGraph()
        graph.add_node("node1")
        graph.add_node("node2")
        
        conn = NodeConnection("node1", "output0", "node2", "input0")
        graph.add_edge("node1", "node2", conn)
        
        # 创建节点实例
        # node1 是根节点，不应该有必需输入端口
        nodes = {
            "node1": DummyNode(node_id="node1", num_inputs=0),  # 根节点无输入
            "node2": DummyNode(node_id="node2"),
        }
        
        report = validator.validate(graph, nodes)
        
        assert report.is_valid
        assert not report.has_errors()
    
    def test_validate_cycle_detection(self):
        """测试循环依赖检测"""
        validator = WorkflowValidator()
        
        # 创建带循环的图（手动构造，因为 add_edge 会阻止）
        graph = WorkflowGraph()
        graph.add_node("node1")
        graph.add_node("node2")
        graph.add_node("node3")
        
        # 正常添加前两条边
        conn1 = NodeConnection("node1", "output0", "node2", "input0")
        conn2 = NodeConnection("node2", "output0", "node3", "input0")
        graph.add_edge("node1", "node2", conn1)
        graph.add_edge("node2", "node3", conn2)
        
        # 手动添加会形成循环的边（绕过 add_edge 的检查）
        graph._graph.add_edge(
            "node3", "node1",
            connection=NodeConnection("node3", "output0", "node1", "input0")
        )
        
        nodes = {
            "node1": DummyNode(node_id="node1"),
            "node2": DummyNode(node_id="node2"),
            "node3": DummyNode(node_id="node3"),
        }
        
        report = validator.validate(graph, nodes)
        
        assert not report.is_valid
        assert report.has_errors()
        assert any("循环依赖" in e.message for e in report.errors)
    
    def test_validate_missing_node_instance(self):
        """测试缺少节点实例"""
        validator = WorkflowValidator()
        
        graph = WorkflowGraph()
        graph.add_node("node1")
        graph.add_node("node2")
        
        # 只提供 node1 的实例，node2 缺失
        nodes = {
            "node1": DummyNode(node_id="node1"),
        }
        
        report = validator.validate(graph, nodes)
        
        assert not report.is_valid
        assert report.has_errors()
        assert any("没有实例" in e.message for e in report.errors)
    
    def test_validate_extra_node_instance(self):
        """测试多余的节点实例"""
        validator = WorkflowValidator()
        
        graph = WorkflowGraph()
        graph.add_node("node1")
        
        # 提供了图中不存在的 node2 实例
        nodes = {
            "node1": DummyNode(node_id="node1", num_inputs=0),  # 根节点无输入
            "node2": DummyNode(node_id="node2"),
        }
        
        report = validator.validate(graph, nodes)
        
        assert report.is_valid  # 多余实例只是警告
        assert report.has_warnings()
        assert any("不在图中" in w.message for w in report.warnings)
    
    def test_validate_invalid_output_port(self):
        """测试无效的输出端口"""
        validator = WorkflowValidator()
        
        graph = WorkflowGraph()
        graph.add_node("node1")
        graph.add_node("node2")
        
        # 连接到不存在的输出端口
        conn = NodeConnection("node1", "invalid_output", "node2", "input0")
        graph.add_edge("node1", "node2", conn)
        
        nodes = {
            "node1": DummyNode(node_id="node1"),
            "node2": DummyNode(node_id="node2"),
        }
        
        report = validator.validate(graph, nodes)
        
        assert not report.is_valid
        assert report.has_errors()
        assert any("输出端口" in e.message and "不存在" in e.message for e in report.errors)
    
    def test_validate_invalid_input_port(self):
        """测试无效的输入端口"""
        validator = WorkflowValidator()
        
        graph = WorkflowGraph()
        graph.add_node("node1")
        graph.add_node("node2")
        
        # 连接到不存在的输入端口
        conn = NodeConnection("node1", "output0", "node2", "invalid_input")
        graph.add_edge("node1", "node2", conn)
        
        nodes = {
            "node1": DummyNode(node_id="node1"),
            "node2": DummyNode(node_id="node2"),
        }
        
        report = validator.validate(graph, nodes)
        
        assert not report.is_valid
        assert report.has_errors()
        assert any("输入端口" in e.message and "不存在" in e.message for e in report.errors)
    
    def test_validate_isolated_node(self):
        """测试孤立节点"""
        validator = WorkflowValidator()
        
        graph = WorkflowGraph()
        graph.add_node("node1")
        graph.add_node("node2")
        graph.add_node("isolated")  # 孤立节点
        
        conn = NodeConnection("node1", "output0", "node2", "input0")
        graph.add_edge("node1", "node2", conn)
        
        nodes = {
            "node1": DummyNode(node_id="node1", num_inputs=0),  # 根节点无输入
            "node2": DummyNode(node_id="node2"),
            "isolated": DummyNode(node_id="isolated", num_inputs=0),  # 孤立节点无输入
        }
        
        report = validator.validate(graph, nodes)
        
        assert report.is_valid  # 孤立节点只是警告
        assert report.has_warnings()
        assert any("孤立" in w.message for w in report.warnings)
    
    def test_validate_missing_required_input(self):
        """测试缺少必需输入"""
        validator = WorkflowValidator()
        
        graph = WorkflowGraph()
        graph.add_node("node1")
        graph.add_node("node2")
        graph.add_node("node3")
        
        # 连接 node1 -> node2，但 node3 有两个必需输入，只连接了一个
        conn1 = NodeConnection("node1", "output0", "node2", "input0")
        graph.add_edge("node1", "node2", conn1)
        
        # node3 有两个必需输入端口
        node3 = DummyNode(node_id="node3", num_inputs=2)
        
        # 只连接 node2 到 node3 的第一个输入
        conn2 = NodeConnection("node2", "output0", "node3", "input0")
        graph.add_edge("node2", "node3", conn2)
        
        nodes = {
            "node1": DummyNode(node_id="node1"),
            "node2": DummyNode(node_id="node2"),
            "node3": node3,
        }
        
        report = validator.validate(graph, nodes)
        
        assert not report.is_valid
        assert report.has_errors()
        assert any("必需的输入端口" in e.message and "input1" in e.message for e in report.errors)
    
    def test_validate_optional_input_not_connected(self):
        """测试可选输入未连接（应该通过）"""
        validator = WorkflowValidator()
        
        graph = WorkflowGraph()
        graph.add_node("node1")
        
        # 创建有可选输入的节点
        node1 = DummyNode(node_id="node1")
        node1.input_ports = [
            NodeInputPort(name="input0", label="输入0", required=False)  # 可选
        ]
        
        nodes = {"node1": node1}
        
        report = validator.validate(graph, nodes)
        
        # 可选输入未连接应该通过验证
        assert report.is_valid
    
    def test_validate_root_node_with_required_input(self):
        """测试根节点定义了必需输入端口（应该报错）"""
        validator = WorkflowValidator()
        
        graph = WorkflowGraph()
        graph.add_node("node1")
        
        # 根节点有必需输入端口，但没有前驱
        nodes = {
            "node1": DummyNode(node_id="node1", num_inputs=1),  # 有必需输入
        }
        
        report = validator.validate(graph, nodes)
        
        # 应该报错
        assert not report.is_valid
        assert report.has_errors()
        # 检查错误信息中包含"根节点"相关提示
        assert any(
            "根节点" in e.message and "必需的输入端口" in e.message 
            for e in report.errors
        )
        # 检查详情中标记了是根节点
        assert any(
            e.details.get("is_root_node") == True
            for e in report.errors
        )
    
    def test_validate_root_node_without_required_input(self):
        """测试根节点没有必需输入端口（应该通过）"""
        validator = WorkflowValidator()
        
        graph = WorkflowGraph()
        graph.add_node("node1")
        
        # 根节点没有输入端口或只有可选输入
        node1 = DummyNode(node_id="node1", num_inputs=0)
        node1.input_ports = []  # 没有输入端口
        
        nodes = {"node1": node1}
        
        report = validator.validate(graph, nodes)
        
        # 应该通过验证（可能有孤立节点警告）
        assert report.is_valid
    
    def test_validate_and_raise_success(self):
        """测试验证并抛出异常（成功情况）"""
        validator = WorkflowValidator()
        
        graph = WorkflowGraph()
        graph.add_node("node1")
        graph.add_node("node2")
        
        conn = NodeConnection("node1", "output0", "node2", "input0")
        graph.add_edge("node1", "node2", conn)
        
        nodes = {
            "node1": DummyNode(node_id="node1", num_inputs=0),  # 根节点无输入
            "node2": DummyNode(node_id="node2"),
        }
        
        # 应该不抛出异常
        validator.validate_and_raise(graph, nodes)
    
    def test_validate_and_raise_failure(self):
        """测试验证并抛出异常（失败情况）"""
        validator = WorkflowValidator()
        
        graph = WorkflowGraph()
        graph.add_node("node1")
        graph.add_node("node2")
        
        # node2 缺少实例
        nodes = {
            "node1": DummyNode(node_id="node1"),
        }
        
        with pytest.raises(WorkflowValidationError, match="验证失败"):
            validator.validate_and_raise(graph, nodes)
    
    def test_quick_validate_success(self):
        """测试快速验证（成功）"""
        validator = WorkflowValidator()
        
        graph = WorkflowGraph()
        graph.add_node("node1")
        graph.add_node("node2")
        
        conn = NodeConnection("node1", "output0", "node2", "input0")
        graph.add_edge("node1", "node2", conn)
        
        assert validator.quick_validate(graph)
    
    def test_quick_validate_with_cycle(self):
        """测试快速验证（有循环）"""
        validator = WorkflowValidator()
        
        graph = WorkflowGraph()
        graph.add_node("node1")
        graph.add_node("node2")
        
        conn1 = NodeConnection("node1", "output0", "node2", "input0")
        graph.add_edge("node1", "node2", conn1)
        
        # 手动添加循环
        graph._graph.add_edge(
            "node2", "node1",
            connection=NodeConnection("node2", "output0", "node1", "input0")
        )
        
        assert not validator.quick_validate(graph)
    
    def test_complex_workflow_validation(self):
        """测试复杂工作流验证"""
        validator = WorkflowValidator()
        
        # 创建复杂图
        graph = WorkflowGraph()
        for i in range(1, 6):
            graph.add_node(f"node{i}")
        
        # node1 -> node2, node3
        # node2 -> node4 (input0)
        # node3 -> node4 (input1)  # 使用不同的端口
        # node4 -> node5
        conn1 = NodeConnection("node1", "output0", "node2", "input0")
        conn2 = NodeConnection("node1", "output0", "node3", "input0")
        conn3 = NodeConnection("node2", "output0", "node4", "input0")
        conn4 = NodeConnection("node3", "output0", "node4", "input1")  # 连接到不同的端口
        conn5 = NodeConnection("node4", "output0", "node5", "input0")
        
        graph.add_edge("node1", "node2", conn1)
        graph.add_edge("node1", "node3", conn2)
        graph.add_edge("node2", "node4", conn3)
        graph.add_edge("node3", "node4", conn4)
        graph.add_edge("node4", "node5", conn5)
        
        # 创建节点实例
        nodes = {}
        for i in range(1, 6):
            # node1 是根节点，无输入
            if i == 1:
                nodes[f"node{i}"] = DummyNode(node_id=f"node{i}", num_inputs=0)
            # node4 有两个输入端口
            elif i == 4:
                nodes[f"node{i}"] = DummyNode(node_id=f"node{i}", num_inputs=2)
            else:
                nodes[f"node{i}"] = DummyNode(node_id=f"node{i}")
        
        report = validator.validate(graph, nodes)
        
        assert report.is_valid
        assert not report.has_errors()
    
    def test_validate_multiple_connections_to_same_input_port(self):
        """测试验证同一个输入端口有多个连接的情况"""
        validator = WorkflowValidator()
        
        # 创建图
        graph = WorkflowGraph()
        graph.add_node("source1")
        graph.add_node("source2")
        graph.add_node("target")
        
        # 两个源节点连接到目标节点的同一个输入端口
        conn1 = NodeConnection("source1", "output0", "target", "input0")
        conn2 = NodeConnection("source2", "output0", "target", "input0")  # 重复连接到 input0
        
        graph.add_edge("source1", "target", conn1)
        graph.add_edge("source2", "target", conn2)
        
        # 创建节点实例
        nodes = {
            "source1": DummyNode(node_id="source1", num_inputs=0),
            "source2": DummyNode(node_id="source2", num_inputs=0),
            "target": DummyNode(node_id="target"),
        }
        
        # 验证
        report = validator.validate(graph, nodes)
        
        # 应该有错误
        assert not report.is_valid
        assert report.has_errors()
        
        # 应该有关于多个连接到同一端口的错误
        error_messages = [str(issue) for issue in report.errors]
        assert any("input0" in msg and "个连接" in msg for msg in error_messages)


class TestValidatorWithStaticInputs:
    """测试验证器对静态输入的支持"""
    
    def test_validate_with_complete_static_inputs(self):
        """测试完整的静态输入验证通过"""
        from deepeye.runtime.context import ExecutionContext
        from deepeye.nodes.io.input import NodeInput
        
        validator = WorkflowValidator()
        
        # 创建图
        graph = WorkflowGraph()
        graph.add_node("node1")
        
        # 创建节点（根节点有必需输入）
        nodes = {
            "node1": DummyNode(node_id="node1", num_inputs=1),
        }
        
        # 创建上下文并设置完整的静态输入
        context = ExecutionContext(workflow_id="test", execution_id="test")
        # DummyNode 的端口名为 "input0"，有一个必需参数 "data"
        context.set_node_input("node1", "input0", NodeInput(data="test_value"))
        
        # 验证（应该通过，因为有完整的静态输入）
        report = validator.validate(graph, nodes, context)
        
        # 应该通过验证
        assert report.is_valid
        assert not report.has_errors()
    
    def test_validate_with_incomplete_static_inputs(self):
        """测试不完整的静态输入验证失败"""
        from deepeye.runtime.context import ExecutionContext
        from deepeye.nodes.io.input import NodeInput, NodeInputSchema
        from deepeye.nodes.io.output import NodeOutput
        from deepeye.nodes.base import BaseNode
        
        validator = WorkflowValidator()
        
        # 创建一个有多个必需参数的自定义节点
        class MultiParamNode(BaseNode):
            node_type = "MultiParam"
            
            def __init__(self, node_id: str):
                from deepeye.nodes.io import NodeOutputPort
                
                super().__init__(node_id=node_id)
                self.metadata = NodeMetadata(
                    name="MultiParam",
                    display_name="多参数节点"
                )
                # 定义一个端口，有多个必需参数
                self.input_ports = [
                    NodeInputPort(
                        name="config",
                        label="配置",
                        required=True,
                        schemas=[
                            NodeInputSchema(name="param1", type="string", required=True),
                            NodeInputSchema(name="param2", type="number", required=True),
                            NodeInputSchema(name="param3", type="string", required=False),
                        ]
                    )
                ]
                self.output_ports = [
                    NodeOutputPort(name="output", label="输出")
                ]
            
            def execute(self, inputs):
                return {"output": NodeOutput(result="ok")}
        
        # 创建图
        graph = WorkflowGraph()
        graph.add_node("node1")
        
        # 创建节点
        nodes = {
            "node1": MultiParamNode(node_id="node1"),
        }
        
        # 创建上下文并设置不完整的静态输入（只有 param1，缺少 param2）
        context = ExecutionContext(workflow_id="test", execution_id="test")
        context.set_node_input("node1", "config", NodeInput(param1="value1"))
        
        # 验证（应该失败，因为缺少必需参数 param2）
        report = validator.validate(graph, nodes, context)
        
        # 应该有错误
        assert not report.is_valid
        assert report.has_errors()
        
        # 应该有关于缺少必需参数的错误
        error_messages = [str(issue) for issue in report.errors]
        assert any("param2" in msg and "缺少必需参数" in msg for msg in error_messages)
    
    def test_validate_with_no_static_inputs_root_node(self):
        """测试根节点没有静态输入验证失败"""
        from deepeye.runtime.context import ExecutionContext
        
        validator = WorkflowValidator()
        
        # 创建图
        graph = WorkflowGraph()
        graph.add_node("node1")
        
        # 创建节点（根节点有必需输入）
        nodes = {
            "node1": DummyNode(node_id="node1", num_inputs=1),
        }
        
        # 创建上下文但不设置静态输入
        context = ExecutionContext(workflow_id="test", execution_id="test")
        
        # 验证（应该失败，因为根节点有必需输入但没有连接或静态输入）
        report = validator.validate(graph, nodes, context)
        
        # 应该有错误
        assert not report.is_valid
        assert report.has_errors()
        
        # 应该有关于根节点缺少输入的错误
        error_messages = [str(issue) for issue in report.errors]
        assert any("根节点" in msg and "input0" in msg for msg in error_messages)
    
    def test_validate_with_static_inputs_all_params_provided(self):
        """测试静态输入包含所有必需参数验证通过"""
        from deepeye.runtime.context import ExecutionContext
        from deepeye.nodes.io.input import NodeInput, NodeInputSchema
        from deepeye.nodes.io.output import NodeOutput
        from deepeye.nodes.base import BaseNode
        
        validator = WorkflowValidator()
        
        # 创建一个有多个必需参数的自定义节点
        class MultiParamNode(BaseNode):
            node_type = "MultiParam"
            
            def __init__(self, node_id: str):
                from deepeye.nodes.io import NodeOutputPort
                
                super().__init__(node_id=node_id)
                self.metadata = NodeMetadata(
                    name="MultiParam",
                    display_name="多参数节点"
                )
                # 定义一个端口，有多个必需参数和可选参数
                self.input_ports = [
                    NodeInputPort(
                        name="config",
                        label="配置",
                        required=True,
                        schemas=[
                            NodeInputSchema(name="param1", type="string", required=True),
                            NodeInputSchema(name="param2", type="number", required=True),
                            NodeInputSchema(name="param3", type="string", required=False),
                        ]
                    )
                ]
                self.output_ports = [
                    NodeOutputPort(name="output", label="输出")
                ]
            
            def execute(self, inputs):
                return {"output": NodeOutput(result="ok")}
        
        # 创建图
        graph = WorkflowGraph()
        graph.add_node("node1")
        
        # 创建节点
        nodes = {
            "node1": MultiParamNode(node_id="node1"),
        }
        
        # 创建上下文并设置完整的静态输入（提供所有必需参数，可选参数可不提供）
        context = ExecutionContext(workflow_id="test", execution_id="test")
        context.set_node_input("node1", "config", NodeInput(param1="value1", param2=123))
        
        # 验证（应该通过，因为所有必需参数都提供了）
        report = validator.validate(graph, nodes, context)
        
        # 应该通过验证
        assert report.is_valid
        assert not report.has_errors()

