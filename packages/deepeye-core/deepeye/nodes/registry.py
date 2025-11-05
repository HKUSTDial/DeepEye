"""节点注册表

管理所有节点类型的注册和创建。
"""

from typing import Dict, Type, Optional, List
from deepeye.nodes.base import BaseNode
from deepeye.exceptions import NodeError


class NodeRegistry:
    """节点注册表
    
    单例模式，管理所有节点类型的注册和实例化。
    
    Example:
        >>> # 注册节点
        >>> registry = NodeRegistry()
        >>> registry.register(MyCustomNode)
        >>> 
        >>> # 创建节点实例
        >>> node = registry.create_node("MyCustomNode", config={"key": "value"})
        >>> 
        >>> # 列出所有节点类型
        >>> node_types = registry.list_node_types()
    """
    
    _instance: Optional["NodeRegistry"] = None
    _nodes: Dict[str, Type[BaseNode]] = {}
    
    def __new__(cls) -> "NodeRegistry":
        """单例模式"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def register(
        self, 
        node_class: Type[BaseNode],
        node_type: Optional[str] = None,
        override: bool = False
    ) -> None:
        """注册节点类
        
        Args:
            node_class: 节点类
            node_type: 节点类型名称，如果为None则使用节点类的node_type属性
            override: 是否覆盖已存在的节点类型
            
        Raises:
            NodeError: 节点类型已存在且不允许覆盖
            
        Example:
            >>> class MyNode(BaseNode):
            ...     node_type = "MyNode"
            ...     def execute(self, inputs):
            ...         return NodeOutput(data=inputs.data)
            >>> 
            >>> registry = NodeRegistry()
            >>> registry.register(MyNode)
        """
        if not issubclass(node_class, BaseNode):
            raise NodeError(
                f"节点类 {node_class.__name__} 必须继承自 BaseNode"
            )
        
        type_name = node_type or getattr(node_class, "node_type", node_class.__name__)
        
        if type_name in self._nodes and not override:
            raise NodeError(
                f"节点类型 '{type_name}' 已存在，如需覆盖请设置 override=True"
            )
        
        self._nodes[type_name] = node_class
    
    def unregister(self, node_type: str) -> None:
        """注销节点类型
        
        Args:
            node_type: 节点类型名称
            
        Raises:
            NodeError: 节点类型不存在
        """
        if node_type not in self._nodes:
            raise NodeError(f"节点类型 '{node_type}' 不存在")
        
        del self._nodes[node_type]
    
    def get_node_class(self, node_type: str) -> Type[BaseNode]:
        """获取节点类
        
        Args:
            node_type: 节点类型名称
            
        Returns:
            节点类
            
        Raises:
            NodeError: 节点类型不存在
        """
        if node_type not in self._nodes:
            raise NodeError(
                f"节点类型 '{node_type}' 不存在。"
                f"可用的节点类型: {', '.join(self._nodes.keys())}"
            )
        
        return self._nodes[node_type]
    
    def create_node(
        self,
        node_type: str,
        node_id: Optional[str] = None,
        config: Optional[dict] = None,
    ) -> BaseNode:
        """创建节点实例
        
        Args:
            node_type: 节点类型名称
            node_id: 节点ID，如果为None则自动生成
            config: 节点配置
            
        Returns:
            节点实例
            
        Raises:
            NodeError: 节点类型不存在或创建失败
            
        Example:
            >>> registry = NodeRegistry()
            >>> node = registry.create_node(
            ...     "MyNode",
            ...     node_id="node-123",
            ...     config={"param": "value"}
            ... )
        """
        node_class = self.get_node_class(node_type)
        
        try:
            return node_class(node_id=node_id, config=config)
        except Exception as e:
            raise NodeError(
                f"创建节点 '{node_type}' 失败: {type(e).__name__}: {str(e)}"
            )
    
    def is_registered(self, node_type: str) -> bool:
        """检查节点类型是否已注册
        
        Args:
            node_type: 节点类型名称
            
        Returns:
            是否已注册
        """
        return node_type in self._nodes
    
    def list_node_types(self) -> List[str]:
        """列出所有已注册的节点类型
        
        Returns:
            节点类型名称列表
        """
        return list(self._nodes.keys())
    
    def list_nodes(self) -> Dict[str, Type[BaseNode]]:
        """列出所有已注册的节点类
        
        Returns:
            节点类型到节点类的映射
        """
        return self._nodes.copy()
    
    def get_node_info(self, node_type: str) -> dict:
        """获取节点类型信息
        
        Args:
            node_type: 节点类型名称
            
        Returns:
            节点信息字典
            
        Raises:
            NodeError: 节点类型不存在
        """
        node_class = self.get_node_class(node_type)
        
        # 创建一个临时实例来获取元数据
        try:
            temp_node = node_class()
            return {
                "node_type": node_type,
                "class_name": node_class.__name__,
                "metadata": temp_node.metadata.model_dump(),
                "input_ports": [
                    {
                        "name": port.name,
                        "label": port.label,
                        "schemas": [schema.model_dump() for schema in port.schemas]
                    }
                    for port in temp_node.input_ports
                ],
                "output_ports": [
                    {
                        "name": port.name,
                        "label": port.label,
                        "schemas": [schema.model_dump() for schema in port.schemas]
                    }
                    for port in temp_node.output_ports
                ],
            }
        except Exception as e:
            return {
                "node_type": node_type,
                "class_name": node_class.__name__,
                "error": f"无法创建临时实例: {str(e)}"
            }
    
    def clear(self) -> None:
        """清空注册表"""
        self._nodes.clear()


# 全局注册表实例
_global_registry = NodeRegistry()


def register_node(
    node_class: Type[BaseNode],
    node_type: Optional[str] = None,
    override: bool = False
) -> None:
    """注册节点类到全局注册表
    
    这是一个便捷函数，可以作为装饰器使用。
    
    Args:
        node_class: 节点类
        node_type: 节点类型名称
        override: 是否覆盖已存在的节点类型
        
    Example:
        >>> @register_node
        ... class MyNode(BaseNode):
        ...     node_type = "MyNode"
        ...     def execute(self, inputs):
        ...         return NodeOutput(data=inputs.data)
    """
    _global_registry.register(node_class, node_type, override)


def get_registry() -> NodeRegistry:
    """获取全局注册表实例
    
    Returns:
        全局节点注册表
    """
    return _global_registry


