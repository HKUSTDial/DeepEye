"""测试工作流引擎"""

import json
import tempfile
from pathlib import Path
import pytest

from deepeye.workflow.engine import Workflow, WorkflowMetadata
from deepeye.nodes import BaseNode, NodeOutput, NodeMetadata, NodeInputPort, get_registry
from deepeye.nodes.io import NodeOutputPort
from deepeye.exceptions import WorkflowError, WorkflowValidationError


class DummyNode(BaseNode):
    """测试用虚拟节点"""
    
    node_type = "Dummy"
    
    def __init__(self, node_id=None, config=None, num_inputs=1, num_outputs=1):
        super().__init__(node_id, config)
        self.metadata = NodeMetadata(name="Dummy", display_name="虚拟节点")
        
        self.input_ports = [
            NodeInputPort(name=f"input{i}", label=f"输入{i}", required=True)
            for i in range(num_inputs)
        ]
        
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


class TestWorkflowMetadata:
    """测试工作流元数据"""
    
    def test_create_metadata(self):
        """测试创建元数据"""
        metadata = WorkflowMetadata(
            name="测试工作流",
            description="测试描述",
            version="1.0.0",
            author="测试作者",
            tags=["test", "demo"]
        )
        
        assert metadata.name == "测试工作流"
        assert metadata.description == "测试描述"
        assert metadata.version == "1.0.0"
        assert metadata.author == "测试作者"
        assert metadata.tags == ["test", "demo"]
        assert metadata.created_at is not None
        assert metadata.updated_at is not None
    
    def test_metadata_to_dict(self):
        """测试元数据转字典"""
        metadata = WorkflowMetadata(name="测试", description="描述")
        data = metadata.model_dump()
        
        assert data["name"] == "测试"
        assert data["description"] == "描述"
        assert "created_at" in data
        assert "updated_at" in data


class TestWorkflow:
    """测试工作流"""
    
    def test_create_workflow(self):
        """测试创建工作流"""
        workflow = Workflow(name="测试工作流", description="测试描述")
        
        assert workflow.metadata.name == "测试工作流"
        assert workflow.metadata.description == "测试描述"
        assert workflow.workflow_id is not None
        assert len(workflow.list_nodes()) == 0
    
    def test_create_workflow_with_custom_id(self):
        """测试使用自定义ID创建工作流"""
        workflow = Workflow(name="测试", workflow_id="custom-id")
        
        assert workflow.workflow_id == "custom-id"
    
    def test_add_node(self):
        """测试添加节点"""
        workflow = Workflow(name="测试")
        node = DummyNode()
        
        result = workflow.add_node("node1", node)
        
        # 支持链式调用
        assert result is workflow
        
        # 节点已添加
        assert len(workflow.list_nodes()) == 1
        assert workflow.get_node("node1") is node
    
    def test_add_duplicate_node_raises_error(self):
        """测试添加重复节点抛出异常"""
        workflow = Workflow(name="测试")
        workflow.add_node("node1", DummyNode())
        
        with pytest.raises(WorkflowError, match="已存在"):
            workflow.add_node("node1", DummyNode())
    
    def test_remove_node(self):
        """测试删除节点"""
        workflow = Workflow(name="测试")
        workflow.add_node("node1", DummyNode())
        workflow.add_node("node2", DummyNode())
        
        result = workflow.remove_node("node1")
        
        # 支持链式调用
        assert result is workflow
        
        # 节点已删除
        assert len(workflow.list_nodes()) == 1
        with pytest.raises(WorkflowError):
            workflow.get_node("node1")
    
    def test_connect_nodes(self):
        """测试连接节点"""
        workflow = Workflow(name="测试")
        workflow.add_node("node1", DummyNode(num_inputs=0))
        workflow.add_node("node2", DummyNode())
        
        result = workflow.connect("node1", "node2")
        
        # 支持链式调用
        assert result is workflow
        
        # 连接已创建
        connections = workflow.get_connections()
        assert len(connections) == 1
        assert connections[0].from_node_id == "node1"
        assert connections[0].to_node_id == "node2"
    
    def test_add_connection(self):
        """测试 add_connection 方法"""
        workflow = Workflow(name="测试")
        workflow.add_node("node1", DummyNode(num_inputs=0))
        workflow.add_node("node2", DummyNode())
        
        workflow.add_connection("node1", "node2")
        
        assert len(workflow.get_connections()) == 1
    
    def test_remove_connection(self):
        """测试删除连接"""
        workflow = Workflow(name="测试")
        workflow.add_node("node1", DummyNode(num_inputs=0))
        workflow.add_node("node2", DummyNode())
        workflow.connect("node1", "node2")
        
        result = workflow.remove_connection("node1", "node2")
        
        # 支持链式调用
        assert result is workflow
        
        # 连接已删除
        assert len(workflow.get_connections()) == 0
    
    def test_validate_success(self):
        """测试验证成功"""
        workflow = Workflow(name="测试")
        workflow.add_node("node1", DummyNode(num_inputs=0))
        workflow.add_node("node2", DummyNode())
        workflow.connect("node1", "node2")
        
        assert workflow.validate()
        assert workflow.is_valid()
    
    def test_validate_failure(self):
        """测试验证失败"""
        workflow = Workflow(name="测试")
        workflow.add_node("node1", DummyNode())  # 根节点有必需输入
        
        assert not workflow.validate()
        assert not workflow.is_valid()
    
    def test_validate_with_raise(self):
        """测试验证失败时抛出异常"""
        workflow = Workflow(name="测试")
        workflow.add_node("node1", DummyNode())
        
        with pytest.raises(WorkflowValidationError):
            workflow.validate(raise_on_error=True)
    
    def test_get_validation_report(self):
        """测试获取验证报告"""
        workflow = Workflow(name="测试")
        workflow.add_node("node1", DummyNode(num_inputs=0))
        
        report = workflow.get_validation_report()
        assert report is not None
        assert report.is_valid
    
    def test_to_dict(self):
        """测试导出为字典"""
        workflow = Workflow(name="测试工作流", description="测试描述")
        workflow.add_node("node1", DummyNode(num_inputs=0))
        workflow.add_node("node2", DummyNode())
        workflow.connect("node1", "node2")
        
        data = workflow.to_dict()
        
        assert data["workflow_id"] == workflow.workflow_id
        assert data["metadata"]["name"] == "测试工作流"
        assert data["metadata"]["description"] == "测试描述"
        assert "graph" in data
        assert "nodes" in data
        assert len(data["nodes"]) == 2
        assert "node1" in data["nodes"]
        assert "node2" in data["nodes"]
    
    def test_to_json(self):
        """测试导出为JSON"""
        workflow = Workflow(name="测试")
        workflow.add_node("node1", DummyNode(num_inputs=0))
        
        json_str = workflow.to_json()
        
        # 验证是有效的JSON
        data = json.loads(json_str)
        assert data["metadata"]["name"] == "测试"
    
    def test_save_and_load(self):
        """测试保存和加载"""
        workflow = Workflow(name="测试工作流")
        workflow.add_node("node1", DummyNode(num_inputs=0))
        workflow.add_node("node2", DummyNode())
        workflow.connect("node1", "node2")
        
        # 保存到临时文件
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            temp_path = f.name
        
        try:
            workflow.save(temp_path)
            
            # 验证文件存在
            assert Path(temp_path).exists()
            
            # 加载（不使用节点注册表）
            loaded = Workflow.load(temp_path)
            
            assert loaded.workflow_id == workflow.workflow_id
            assert loaded.metadata.name == workflow.metadata.name
            assert loaded.graph.node_count() == 2
            assert loaded.graph.edge_count() == 1
        finally:
            # 清理
            Path(temp_path).unlink(missing_ok=True)
    
    def test_from_dict_without_registry(self):
        """测试从字典创建工作流（不使用注册表）"""
        workflow = Workflow(name="原始")
        workflow.add_node("node1", DummyNode(num_inputs=0))
        
        data = workflow.to_dict()
        loaded = Workflow.from_dict(data)
        
        assert loaded.workflow_id == workflow.workflow_id
        assert loaded.metadata.name == "原始"
        assert loaded.graph.node_count() == 1
        # 注意：没有注册表时，节点实例不会被创建
        assert len(loaded.nodes) == 0
    
    def test_from_json(self):
        """测试从JSON创建工作流"""
        workflow = Workflow(name="测试")
        workflow.add_node("node1", DummyNode(num_inputs=0))
        
        json_str = workflow.to_json()
        loaded = Workflow.from_json(json_str)
        
        assert loaded.metadata.name == "测试"
    
    def test_get_execution_order(self):
        """测试获取执行顺序"""
        workflow = Workflow(name="测试")
        workflow.add_node("node1", DummyNode(num_inputs=0))
        workflow.add_node("node2", DummyNode())
        workflow.add_node("node3", DummyNode())
        workflow.connect("node1", "node2")
        workflow.connect("node2", "node3")
        
        order = workflow.get_execution_order()
        
        assert len(order) == 3
        assert order.index("node1") < order.index("node2")
        assert order.index("node2") < order.index("node3")
    
    def test_get_node_dependencies(self):
        """测试获取节点依赖"""
        workflow = Workflow(name="测试")
        workflow.add_node("node1", DummyNode(num_inputs=0))
        workflow.add_node("node2", DummyNode(num_inputs=0))
        workflow.add_node("node3", DummyNode(num_inputs=2))
        workflow.connect("node1", "node3", to_port="input0")
        workflow.connect("node2", "node3", to_port="input1")
        
        deps = workflow.get_node_dependencies("node3")
        
        assert len(deps) == 2
        assert "node1" in deps
        assert "node2" in deps
    
    def test_get_node_dependents(self):
        """测试获取依赖节点的节点"""
        workflow = Workflow(name="测试")
        workflow.add_node("node1", DummyNode(num_inputs=0))
        workflow.add_node("node2", DummyNode())
        workflow.add_node("node3", DummyNode())
        workflow.connect("node1", "node2")
        workflow.connect("node1", "node3")
        
        dependents = workflow.get_node_dependents("node1")
        
        assert len(dependents) == 2
        assert "node2" in dependents
        assert "node3" in dependents
    
    def test_get_execution_layers(self):
        """测试获取执行层级"""
        workflow = Workflow(name="测试")
        workflow.add_node("node1", DummyNode(num_inputs=0))
        workflow.add_node("node2", DummyNode())
        workflow.add_node("node3", DummyNode())
        workflow.add_node("node4", DummyNode(num_inputs=2))
        
        workflow.connect("node1", "node2")
        workflow.connect("node1", "node3")
        workflow.connect("node2", "node4", to_port="input0")
        workflow.connect("node3", "node4", to_port="input1")
        
        layers = workflow.get_execution_layers()
        
        assert len(layers) == 3
        assert layers[0] == ["node1"]
        assert set(layers[1]) == {"node2", "node3"}
        assert layers[2] == ["node4"]
    
    def test_get_root_nodes(self):
        """测试获取根节点"""
        workflow = Workflow(name="测试")
        workflow.add_node("node1", DummyNode(num_inputs=0))
        workflow.add_node("node2", DummyNode(num_inputs=0))
        workflow.add_node("node3", DummyNode())
        workflow.connect("node1", "node3")
        workflow.connect("node2", "node3", to_port="input0")
        
        roots = workflow.get_root_nodes()
        
        assert len(roots) == 2
        assert "node1" in roots
        assert "node2" in roots
    
    def test_get_leaf_nodes(self):
        """测试获取叶子节点"""
        workflow = Workflow(name="测试")
        workflow.add_node("node1", DummyNode(num_inputs=0))
        workflow.add_node("node2", DummyNode())
        workflow.add_node("node3", DummyNode())
        workflow.connect("node1", "node2")
        workflow.connect("node1", "node3")
        
        leaves = workflow.get_leaf_nodes()
        
        assert len(leaves) == 2
        assert "node2" in leaves
        assert "node3" in leaves
    
    def test_has_node(self):
        """测试检查节点是否存在"""
        workflow = Workflow(name="测试")
        workflow.add_node("node1", DummyNode())
        
        assert workflow.has_node("node1")
        assert not workflow.has_node("node2")
    
    def test_connect_ports(self):
        """测试 connect_ports 方法"""
        workflow = Workflow(name="测试")
        workflow.add_node("node1", DummyNode(num_inputs=0, num_outputs=2))
        workflow.add_node("node2", DummyNode(num_inputs=2))
        
        workflow.connect_ports("node1", "output1", "node2", "input1")
        
        connections = workflow.get_connections()
        assert len(connections) == 1
        assert connections[0].from_port == "output1"
        assert connections[0].to_port == "input1"
    
    def test_clear(self):
        """测试清空工作流"""
        workflow = Workflow(name="测试")
        workflow.add_node("node1", DummyNode(num_inputs=0))
        workflow.add_node("node2", DummyNode())
        workflow.connect("node1", "node2")
        
        workflow_id = workflow.workflow_id
        name = workflow.metadata.name
        
        workflow.clear()
        
        # 节点和连接已清空
        assert len(workflow.list_nodes()) == 0
        assert len(workflow.get_connections()) == 0
        
        # ID和名称保留
        assert workflow.workflow_id == workflow_id
        assert workflow.metadata.name == name
    
    def test_chain_operations(self):
        """测试链式操作"""
        workflow = (Workflow(name="链式测试")
                    .add_node("node1", DummyNode(num_inputs=0))
                    .add_node("node2", DummyNode())
                    .add_node("node3", DummyNode())
                    .connect("node1", "node2")
                    .connect("node2", "node3"))
        
        assert len(workflow.list_nodes()) == 3
        assert len(workflow.get_connections()) == 2
    
    def test_repr(self):
        """测试字符串表示"""
        workflow = Workflow(name="测试工作流")
        workflow.add_node("node1", DummyNode(num_inputs=0))
        workflow.add_node("node2", DummyNode())
        workflow.connect("node1", "node2")
        
        repr_str = repr(workflow)
        assert "Workflow" in repr_str
        assert "测试工作流" in repr_str
        assert "nodes=2" in repr_str
        assert "connections=1" in repr_str

