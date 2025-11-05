"""测试 Tool Layer"""

import pytest

from deepeye.agent.tool_layer import (
    ToolRegistry,
    ToolDescription,
    PortDescription,
    PortParameterDescription,
)
from deepeye.nodes.base import BaseNode, NodeMetadata
from deepeye.nodes.io import (
    NodeInput,
    NodeOutput,
    NodeInputPort,
    NodeOutputPort,
    NodeInputSchema,
    NodeOutputSchema,
)


class MockNode(BaseNode):
    """模拟节点用于测试"""
    
    node_type = "MockNode"
    
    def __init__(self, node_id=None, config=None):
        super().__init__(node_id, config)
        
        self.metadata = NodeMetadata(
            name="MockNode",
            display_name="模拟节点",
            description="用于测试的模拟节点",
            category="test",
            semantic_description="这是一个测试节点，用于验证工具注册",
            capabilities=["test", "mock"],
            use_cases=["单元测试"],
            input_description={"input": "测试输入"},
            output_description={"output": "测试输出"},
        )
        
        self.input_ports = [
            NodeInputPort(
                name="input",
                label="输入",
                required=True,
                schemas=[
                    NodeInputSchema(
                        name="data",
                        type="string",
                        required=True,
                        description="输入数据"
                    )
                ]
            )
        ]
        
        self.output_ports = [
            NodeOutputPort(
                name="output",
                label="输出",
                schemas=[
                    NodeOutputSchema(
                        name="result",
                        type="string",
                        description="处理结果"
                    )
                ]
            )
        ]
    
    def execute(self, inputs):
        input_data = self.get_single_input(inputs)
        return self.create_single_output(data=f"Processed: {input_data.data}")


class TestPortParameterDescription:
    """测试 PortParameterDescription"""
    
    def test_create_parameter(self):
        """测试创建参数"""
        param = PortParameterDescription(
            name="query",
            type="string",
            description="SQL 查询",
            required=True,
        )
        
        assert param.name == "query"
        assert param.type == "string"
        assert param.required is True
    
    def test_parameter_with_default(self):
        """测试带默认值的参数"""
        param = PortParameterDescription(
            name="mode",
            type="string",
            description="执行模式",
            required=False,
            default="auto",
        )
        
        assert param.default == "auto"
        assert param.required is False


class TestPortDescription:
    """测试 PortDescription"""
    
    def test_create_port(self):
        """测试创建端口描述"""
        port = PortDescription(
            name="query",
            label="查询输入",
            required=True,
            parameters=[
                PortParameterDescription(
                    name="text",
                    type="string",
                    description="查询文本",
                    required=True,
                )
            ],
        )
        
        assert port.name == "query"
        assert port.label == "查询输入"
        assert port.required is True
        assert len(port.parameters) == 1


class TestToolDescription:
    """测试 ToolDescription"""
    
    def test_create_tool_description(self):
        """测试创建工具描述"""
        tool = ToolDescription(
            name="NL2SQL",
            description="将自然语言转换为 SQL",
            input_ports=[
                PortDescription(
                    name="query",
                    label="查询",
                    required=True,
                    parameters=[
                        PortParameterDescription(
                            name="text",
                            type="string",
                            description="自然语言查询",
                            required=True,
                        )
                    ],
                )
            ],
            output_ports=[
                PortDescription(
                    name="result",
                    label="结果",
                    parameters=[
                        PortParameterDescription(
                            name="data",
                            type="object",
                            description="查询结果",
                        )
                    ],
                )
            ],
        )
        
        assert tool.name == "NL2SQL"
        assert len(tool.input_ports) == 1
        assert len(tool.output_ports) == 1


class TestToolRegistry:
    """测试 ToolRegistry"""
    
    def test_create_registry(self):
        """测试创建注册表"""
        registry = ToolRegistry()
        assert len(registry) == 0
    
    def test_register_node(self):
        """测试注册节点"""
        registry = ToolRegistry()
        registry.register_node(MockNode)
        
        assert len(registry) == 1
        assert registry.has_tool("MockNode")
    
    def test_get_tool(self):
        """测试获取工具"""
        registry = ToolRegistry()
        registry.register_node(MockNode)
        
        tool = registry.get_tool("MockNode")
        assert tool is not None
        assert tool.name == "MockNode"
        assert tool.description == "用于测试的模拟节点"
        assert len(tool.input_ports) == 1
        assert len(tool.output_ports) == 1
    
    def test_list_tools(self):
        """测试列出所有工具"""
        registry = ToolRegistry()
        registry.register_node(MockNode)
        
        tools = registry.list_tools()
        assert len(tools) == 1
        assert tools[0].name == "MockNode"
    
    def test_create_node_instance(self):
        """测试创建节点实例"""
        registry = ToolRegistry()
        registry.register_node(MockNode)
        
        node = registry.create_node_instance("MockNode")
        assert node is not None
        assert isinstance(node, MockNode)
        assert node.node_type == "MockNode"
    
    def test_create_node_with_config(self):
        """测试创建带配置的节点实例"""
        registry = ToolRegistry()
        registry.register_node(MockNode)
        
        config = {"param1": "value1"}
        node = registry.create_node_instance("MockNode", config=config)
        assert node is not None
    
    def test_get_tool_names(self):
        """测试获取工具名称列表"""
        registry = ToolRegistry()
        registry.register_node(MockNode)
        
        names = registry.get_tool_names()
        assert names == ["MockNode"]

