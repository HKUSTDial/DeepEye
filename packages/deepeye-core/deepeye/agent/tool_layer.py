"""Tool Layer - 将节点包装为 LLM 可理解的工具

将 DeepEye 的节点系统转换为 LLM Agent 可以理解和使用的工具描述。
"""

from typing import Any, Dict, List, Optional, Type
from pydantic import BaseModel, Field

from deepeye.nodes.base import BaseNode


class PortParameterDescription(BaseModel):
    """端口参数描述"""
    
    name: str = Field(description="参数名称")
    type: str = Field(description="参数类型")
    required: bool = Field(default=False, description="是否必需")
    default: Optional[Any] = Field(default=None, description="默认值")
    description: str = Field(default="", description="参数描述")


class PortDescription(BaseModel):
    """端口描述（输入或输出）"""
    
    name: str = Field(description="端口名称")
    label: str = Field(default="", description="端口显示标签")
    required: bool = Field(default=True, description="是否为必需端口")
    parameters: List[PortParameterDescription] = Field(
        default_factory=list,
        description="该端口的参数列表"
    )


class ToolDescription(BaseModel):
    """工具描述 - LLM 可理解的格式
    
    从节点的端口和 schema 信息提取工具描述。
    """
    
    name: str = Field(description="工具名称（对应节点类型）")
    description: str = Field(description="工具功能描述")
    
    # 输入输出端口描述
    input_ports: List[PortDescription] = Field(
        default_factory=list,
        description="输入端口列表，每个端口包含其参数"
    )
    output_ports: List[PortDescription] = Field(
        default_factory=list,
        description="输出端口列表，每个端口包含其输出参数"
    )


class ToolRegistry:
    """工具注册表
    
    管理节点类型到工具描述的映射，以及工具的实例化。
    """
    
    def __init__(self):
        """初始化工具注册表"""
        self._tools: Dict[str, ToolDescription] = {}
        self._node_classes: Dict[str, Type[BaseNode]] = {}
    
    def register_node(self, node_class: Type[BaseNode]) -> None:
        """注册节点类型为工具
        
        Args:
            node_class: 节点类
        """
        # 创建临时实例来获取元数据和端口信息
        temp_node = node_class()
        metadata = temp_node.metadata
        
        # 从输入端口提取描述
        input_ports = []
        for port in temp_node.input_ports:
            # 从端口的 schemas 提取参数
            parameters = []
            for schema in port.schemas:
                param = PortParameterDescription(
                    name=schema.name,
                    type=schema.type,
                    required=schema.required,
                    default=schema.default,
                    description=schema.description,
                )
                parameters.append(param)
            
            port_desc = PortDescription(
                name=port.name,
                label=port.label or port.name,
                required=port.required,
                parameters=parameters,
            )
            input_ports.append(port_desc)
        
        # 从输出端口提取描述
        output_ports = []
        for port in temp_node.output_ports:
            # 从端口的 schemas 提取参数
            parameters = []
            for schema in port.schemas:
                param = PortParameterDescription(
                    name=schema.name,
                    type=schema.type,
                    required=False,  # 输出参数不需要 required
                    description=schema.description,
                )
                parameters.append(param)
            
            port_desc = PortDescription(
                name=port.name,
                label=port.label or port.name,
                required=False,  # 输出端口不需要 required
                parameters=parameters,
            )
            output_ports.append(port_desc)
        
        # 构建工具描述
        tool_desc = ToolDescription(
            name=metadata.name,
            description=metadata.description or metadata.display_name,
            input_ports=input_ports,
            output_ports=output_ports,
        )
        
        # 保存到注册表
        self._tools[metadata.name] = tool_desc
        self._node_classes[metadata.name] = node_class
    
    def get_tool(self, tool_name: str) -> Optional[ToolDescription]:
        """获取工具描述
        
        Args:
            tool_name: 工具名称
            
        Returns:
            工具描述，如果不存在则返回 None
        """
        return self._tools.get(tool_name)
    
    def list_tools(self) -> List[ToolDescription]:
        """列出所有注册的工具
        
        Returns:
            工具描述列表
        """
        return list(self._tools.values())
    
    def create_node_instance(
        self,
        tool_name: str,
        node_id: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None,
    ) -> Optional[BaseNode]:
        """创建节点实例
        
        Args:
            tool_name: 工具名称（节点类型）
            node_id: 节点实例 ID
            config: 节点配置
            
        Returns:
            节点实例，如果工具不存在则返回 None
        """
        node_class = self._node_classes.get(tool_name)
        if node_class is None:
            return None
        
        return node_class(node_id=node_id, config=config)
    
    def get_tool_names(self) -> List[str]:
        """获取所有工具名称
        
        Returns:
            工具名称列表
        """
        return list(self._tools.keys())
    
    def has_tool(self, tool_name: str) -> bool:
        """检查工具是否存在
        
        Args:
            tool_name: 工具名称
            
        Returns:
            是否存在
        """
        return tool_name in self._tools
    
    def __len__(self) -> int:
        """返回注册的工具数量"""
        return len(self._tools)
    
    def __repr__(self) -> str:
        """字符串表示"""
        return f"<ToolRegistry(tools={len(self._tools)})>"

