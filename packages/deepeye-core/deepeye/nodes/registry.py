"""节点注册表

管理所有节点类型的注册和创建。
"""

from typing import Dict, Type, Optional, List, Union, Callable, overload
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
    
    def __new__(cls) -> "NodeRegistry":
        """单例模式"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            # 初始化实例变量（而不是类变量）
            cls._instance._nodes: Dict[str, Type[BaseNode]] = {}
        return cls._instance
    
    def __init__(self):
        """初始化注册表
        
        注意：由于单例模式，此方法可能被多次调用，但只会初始化一次。
        实际的初始化在 __new__ 中完成。
        """
        # 确保 _nodes 存在（防止模块重新加载时丢失）
        if not hasattr(self, '_nodes'):
            self._nodes: Dict[str, Type[BaseNode]] = {}
    
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
        
        # 检查是否已经注册了相同的类（防止模块重新加载时的重复注册）
        existing_class = self._nodes.get(type_name)
        if existing_class is not None:
            # 如果已经注册了相同的类，静默跳过（避免重复注册）
            if existing_class is node_class:
                return
            
            # 如果注册了不同的类，且不允许覆盖，抛出异常
            if not override:
                raise NodeError(
                    f"节点类型 '{type_name}' 已存在（已注册类: {existing_class.__name__}），"
                    f"如需覆盖请设置 override=True"
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
        validate_on_init: bool = False,
    ) -> BaseNode:
        """创建节点实例
        
        Args:
            node_type: 节点类型名称
            node_id: 节点ID，如果为None则自动生成
            config: 节点配置
            validate_on_init: 是否在初始化时验证配置（默认False）
            
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
            return node_class(node_id=node_id, config=config, validate_on_init=validate_on_init)
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


@overload
def register_node(
    node_class: Type[BaseNode],
    node_type: Optional[str] = None,
    override: bool = False
) -> Type[BaseNode]:
    """直接注册节点类"""
    ...

@overload
def register_node(
    node_class: None = None,
    node_type: Optional[str] = None,
    override: bool = False
) -> Callable[[Type[BaseNode]], Type[BaseNode]]:
    """作为装饰器使用（带参数）"""
    ...

def register_node(
    node_class: Optional[Type[BaseNode]] = None,
    node_type: Optional[str] = None,
    override: bool = False
) -> Union[Type[BaseNode], Callable[[Type[BaseNode]], Type[BaseNode]]]:
    """注册节点类到全局注册表
    
    这是一个便捷函数，可以作为装饰器使用。
    
    Args:
        node_class: 节点类（装饰器模式下为None）
        node_type: 节点类型名称
        override: 是否覆盖已存在的节点类型
        
    Returns:
        装饰器模式下返回被装饰的类或装饰器函数，否则返回类本身
        
    Example:
        >>> @register_node
        ... class MyNode(BaseNode):
        ...     node_type = "MyNode"
        ...     def execute(self, inputs):
        ...         return NodeOutput(data=inputs.data)
        
        >>> @register_node(node_type="CustomNode", override=True)
        ... class AnotherNode(BaseNode):
        ...     def execute(self, inputs):
        ...         return NodeOutput(data=inputs.data)
    """
    def decorator(cls: Type[BaseNode]) -> Type[BaseNode]:
        """装饰器内部函数"""
        _global_registry.register(cls, node_type, override)
        return cls
    
    # 如果直接调用（作为装饰器不带括号），node_class 是类
    if node_class is not None:
        _global_registry.register(node_class, node_type, override)
        return node_class
    
    # 如果带参数调用（作为装饰器带括号），返回装饰器函数
    return decorator


def get_registry() -> NodeRegistry:
    """获取全局注册表实例
    
    Returns:
        全局节点注册表
    """
    return _global_registry


