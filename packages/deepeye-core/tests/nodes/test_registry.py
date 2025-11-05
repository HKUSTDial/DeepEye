"""测试节点注册表"""

import pytest
from deepeye.nodes import (
    BaseNode,
    NodeInput,
    NodeOutput,
    NodeRegistry,
    register_node,
    get_registry,
)
from deepeye.exceptions import NodeError


class DummyNodeA(BaseNode):
    """测试节点A"""
    
    node_type = "DummyNodeA"
    
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
        return self.create_single_output(data="A")


class DummyNodeB(BaseNode):
    """测试节点B"""
    
    node_type = "DummyNodeB"
    
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
        return self.create_single_output(data="B")


def test_registry_singleton():
    """测试注册表单例模式"""
    registry1 = NodeRegistry()
    registry2 = NodeRegistry()
    
    assert registry1 is registry2


def test_register_node():
    """测试注册节点"""
    registry = NodeRegistry()
    registry.clear()  # 清空注册表
    
    registry.register(DummyNodeA)
    
    assert registry.is_registered("DummyNodeA")
    assert "DummyNodeA" in registry.list_node_types()


def test_register_multiple_nodes():
    """测试注册多个节点"""
    registry = NodeRegistry()
    registry.clear()
    
    registry.register(DummyNodeA)
    registry.register(DummyNodeB)
    
    node_types = registry.list_node_types()
    assert "DummyNodeA" in node_types
    assert "DummyNodeB" in node_types
    assert len(node_types) == 2


def test_register_duplicate_error():
    """测试重复注册错误"""
    registry = NodeRegistry()
    registry.clear()
    
    registry.register(DummyNodeA)
    
    with pytest.raises(NodeError, match="已存在"):
        registry.register(DummyNodeA)


def test_register_with_override():
    """测试覆盖注册"""
    registry = NodeRegistry()
    registry.clear()
    
    registry.register(DummyNodeA)
    registry.register(DummyNodeA, override=True)  # 应该成功
    
    assert registry.is_registered("DummyNodeA")


def test_unregister_node():
    """测试注销节点"""
    registry = NodeRegistry()
    registry.clear()
    
    registry.register(DummyNodeA)
    assert registry.is_registered("DummyNodeA")
    
    registry.unregister("DummyNodeA")
    assert not registry.is_registered("DummyNodeA")


def test_unregister_nonexistent():
    """测试注销不存在的节点"""
    registry = NodeRegistry()
    registry.clear()
    
    with pytest.raises(NodeError, match="不存在"):
        registry.unregister("NonExistent")


def test_get_node_class():
    """测试获取节点类"""
    registry = NodeRegistry()
    registry.clear()
    
    registry.register(DummyNodeA)
    
    node_class = registry.get_node_class("DummyNodeA")
    assert node_class is DummyNodeA


def test_get_nonexistent_node_class():
    """测试获取不存在的节点类"""
    registry = NodeRegistry()
    registry.clear()
    
    with pytest.raises(NodeError, match="不存在"):
        registry.get_node_class("NonExistent")


def test_create_node():
    """测试创建节点实例"""
    registry = NodeRegistry()
    registry.clear()
    
    registry.register(DummyNodeA)
    
    node = registry.create_node("DummyNodeA")
    
    assert isinstance(node, DummyNodeA)
    assert node.node_type == "DummyNodeA"


def test_create_node_with_config():
    """测试创建带配置的节点"""
    registry = NodeRegistry()
    registry.clear()
    
    registry.register(DummyNodeA)
    
    node = registry.create_node(
        "DummyNodeA",
        node_id="custom-id",
        config={"param": "value"}
    )
    
    assert node.node_id == "custom-id"


def test_list_node_types():
    """测试列出节点类型"""
    registry = NodeRegistry()
    registry.clear()
    
    registry.register(DummyNodeA)
    registry.register(DummyNodeB)
    
    node_types = registry.list_node_types()
    
    assert isinstance(node_types, list)
    assert len(node_types) == 2
    assert set(node_types) == {"DummyNodeA", "DummyNodeB"}


def test_list_nodes():
    """测试列出节点类"""
    registry = NodeRegistry()
    registry.clear()
    
    registry.register(DummyNodeA)
    registry.register(DummyNodeB)
    
    nodes = registry.list_nodes()
    
    assert isinstance(nodes, dict)
    assert len(nodes) == 2
    assert nodes["DummyNodeA"] is DummyNodeA
    assert nodes["DummyNodeB"] is DummyNodeB


def test_get_node_info():
    """测试获取节点信息"""
    registry = NodeRegistry()
    registry.clear()
    
    registry.register(DummyNodeA)
    
    info = registry.get_node_info("DummyNodeA")
    
    assert info["node_type"] == "DummyNodeA"
    assert info["class_name"] == "DummyNodeA"
    assert "metadata" in info


def test_register_node_decorator():
    """测试注册节点装饰器"""
    # 清空全局注册表
    global_registry = get_registry()
    global_registry.clear()
    
    @register_node
    class DecoratedNode(BaseNode):
        node_type = "DecoratedNode"
        
        def execute(self, inputs: NodeInput) -> NodeOutput:
            return NodeOutput(data="decorated")
    
    assert global_registry.is_registered("DecoratedNode")


def test_get_global_registry():
    """测试获取全局注册表"""
    registry1 = get_registry()
    registry2 = get_registry()
    
    assert registry1 is registry2
    assert isinstance(registry1, NodeRegistry)


def test_clear_registry():
    """测试清空注册表"""
    registry = NodeRegistry()
    registry.clear()
    
    registry.register(DummyNodeA)
    registry.register(DummyNodeB)
    assert len(registry.list_node_types()) == 2
    
    registry.clear()
    assert len(registry.list_node_types()) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])


