"""测试基础节点类"""

import pytest
from deepeye.nodes import (
    BaseNode,
    NodeInput,
    NodeOutput,
    NodeStatus,
    NodeMetadata,
)
from deepeye.exceptions import NodeValidationError


class DummyNode(BaseNode):
    """用于测试的虚拟节点"""
    
    node_type = "DummyNode"
    
    def __init__(self, node_id=None, config=None):
        super().__init__(node_id, config)
        self.metadata = NodeMetadata(
            name="DummyNode",
            display_name="测试节点",
            description="用于测试的虚拟节点"
        )
        # 定义输入/输出端口
        from deepeye.nodes.io import NodeInputPort, NodeOutputPort
        self.input_ports = [
            NodeInputPort(name="data", label="数据输入", required=True)
        ]
        self.output_ports = [
            NodeOutputPort(name="output", label="输出")
        ]
    
    def execute(self, inputs: dict) -> dict:
        """简单地返回输入数据"""
        input_data = self.get_single_input(inputs)
        return self.create_single_output(data=input_data.data)


class ErrorNode(BaseNode):
    """会抛出异常的节点"""
    
    node_type = "ErrorNode"
    
    def __init__(self, node_id=None, config=None):
        super().__init__(node_id, config)
        from deepeye.nodes.io import NodeInputPort, NodeOutputPort
        self.input_ports = [
            NodeInputPort(name="data", label="数据输入", required=True)
        ]
        self.output_ports = [
            NodeOutputPort(name="output", label="输出")
        ]
    
    def execute(self, inputs: dict) -> dict:
        raise ValueError("故意抛出的错误")


def test_node_creation():
    """测试节点创建"""
    node = DummyNode()
    
    assert node.node_id is not None
    assert node.node_type == "DummyNode"
    assert node.get_status() == NodeStatus.PENDING


def test_node_with_custom_id():
    """测试自定义节点ID"""
    custom_id = "custom-node-123"
    node = DummyNode(node_id=custom_id)
    
    assert node.node_id == custom_id


def test_node_execution():
    """测试节点执行"""
    node = DummyNode()
    inputs = {"data": NodeInput(data={"test": "value"})}
    
    outputs = node.run(inputs)
    
    assert isinstance(outputs, dict)
    assert "output" in outputs
    assert outputs["output"].is_success()
    assert outputs["output"].data == {"test": "value"}
    assert node.get_status() == NodeStatus.SUCCESS


def test_node_error_handling():
    """测试节点错误处理"""
    node = ErrorNode()
    inputs = {"data": NodeInput(data={})}
    
    outputs = node.run(inputs)
    
    assert isinstance(outputs, dict)
    assert "output" in outputs
    assert outputs["output"].is_failed()
    assert outputs["output"].error is not None
    assert "ValueError" in outputs["output"].error
    assert node.get_status() == NodeStatus.FAILED


def test_node_reset():
    """测试节点重置"""
    node = DummyNode()
    inputs = {"data": NodeInput(data={})}
    
    # 执行节点
    node.run(inputs)
    assert node.get_status() == NodeStatus.SUCCESS
    
    # 重置节点
    node.reset()
    assert node.get_status() == NodeStatus.PENDING
    assert len(node.get_outputs()) == 0


def test_node_to_dict():
    """测试节点转换为字典"""
    node = DummyNode(node_id="test-123")
    node_dict = node.to_dict()
    
    assert node_dict["node_id"] == "test-123"
    assert node_dict["node_type"] == "DummyNode"
    assert "metadata" in node_dict
    assert node_dict["status"] == "pending"


def test_node_metadata():
    """测试节点元数据"""
    node = DummyNode()
    
    assert node.metadata.name == "DummyNode"
    assert node.metadata.display_name == "测试节点"
    assert node.metadata.description == "用于测试的虚拟节点"


def test_node_output_logs():
    """测试节点输出日志"""
    node = DummyNode()
    inputs = {"data": NodeInput(data={})}
    
    outputs = node.run(inputs)
    output = outputs["output"]
    
    assert len(output.logs) > 0
    assert any("输入验证通过" in log for log in output.logs)
    assert any("节点执行成功" in log for log in output.logs)


def test_node_repr():
    """测试节点字符串表示"""
    node = DummyNode(node_id="test-456")
    
    repr_str = repr(node)
    assert "DummyNode" in repr_str
    assert "test-456" in repr_str
    assert "pending" in repr_str


if __name__ == "__main__":
    pytest.main([__file__, "-v"])


