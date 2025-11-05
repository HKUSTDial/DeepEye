"""节点输入定义

定义节点接收的输入数据结构和验证规则。
"""

from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field, ConfigDict


class NodeInput(BaseModel):
    """节点输入数据模型
    
    节点的输入数据结构，支持多种数据类型和验证。
    
    Attributes:
        data: 主要输入数据，可以是任意类型
        metadata: 元数据信息
        context: 执行上下文信息
        
    Example:
        >>> input_data = NodeInput(
        ...     data={"query": "SELECT * FROM users"},
        ...     metadata={"source": "user_request"},
        ...     context={"user_id": "123"}
        ... )
    """
    
    model_config = ConfigDict(arbitrary_types_allowed=True, extra="allow")
    
    data: Any = Field(
        default=None,
        description="节点的主要输入数据"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="输入数据的元数据信息"
    )
    context: Dict[str, Any] = Field(
        default_factory=dict,
        description="执行上下文信息，如用户ID、会话ID等"
    )
    
    def get(self, key: str, default: Any = None) -> Any:
        """获取输入数据中的值
        
        首先尝试从 data 字典中获取，如果不存在则尝试从额外字段中获取。
        
        Args:
            key: 数据键名
            default: 默认值
            
        Returns:
            对应的值，如果不存在返回默认值
            
        Example:
            >>> node_input = NodeInput(data={"name": "Alice"})
            >>> node_input.get("name")
            'Alice'
            >>> node_input.get("age", 18)
            18
            >>> # 也支持额外字段
            >>> node_input2 = NodeInput(name="Bob", age=30)
            >>> node_input2.get("name")
            'Bob'
        """
        # 首先尝试从 data 字典中获取
        if isinstance(self.data, dict) and key in self.data:
            return self.data[key]
        
        # 如果 data 中没有，尝试从额外字段中获取
        if hasattr(self, key):
            value = getattr(self, key)
            # 确保不返回内置字段
            if key not in ['data', 'metadata', 'context']:
                return value
        
        return default
    
    def update(self, **kwargs: Any) -> None:
        """更新输入数据
        
        Args:
            **kwargs: 要更新的键值对
            
        Example:
            >>> node_input = NodeInput(data={"name": "Alice"})
            >>> node_input.update(age=25)
            >>> node_input.data
            {'name': 'Alice', 'age': 25}
        """
        if not isinstance(self.data, dict):
            self.data = {}
        self.data.update(kwargs)
    
    def has(self, key: str) -> bool:
        """检查是否包含某个键
        
        检查 data 字典或额外字段中是否包含指定的键。
        
        Args:
            key: 数据键名
            
        Returns:
            是否包含该键
        """
        # 检查 data 字典
        if isinstance(self.data, dict) and key in self.data:
            return True
        
        # 检查额外字段
        if hasattr(self, key) and key not in ['data', 'metadata', 'context']:
            return True
        
        return False


class NodeInputSchema(BaseModel):
    """节点输入模式定义
    
    定义节点期望接收的输入结构和验证规则。
    
    Attributes:
        name: 输入参数名称
        type: 输入参数类型
        required: 是否必需
        default: 默认值
        description: 参数描述
        
    Example:
        >>> schema = NodeInputSchema(
        ...     name="query",
        ...     type="string",
        ...     required=True,
        ...     description="SQL查询语句"
        ... )
    """
    
    model_config = ConfigDict(extra="allow")
    
    name: str = Field(
        description="输入参数名称"
    )
    type: str = Field(
        default="any",
        description="输入参数类型，如 string, number, object, array 等"
    )
    required: bool = Field(
        default=False,
        description="是否为必需参数"
    )
    default: Optional[Any] = Field(
        default=None,
        description="默认值"
    )
    description: str = Field(
        default="",
        description="参数描述"
    )
    
    def validate_value(self, value: Any) -> bool:
        """验证值是否符合类型要求
        
        Args:
            value: 要验证的值
            
        Returns:
            是否符合类型要求
        """
        if value is None and not self.required:
            return True
        
        if value is None and self.required:
            return False
        
        # 简单的类型检查
        type_mapping = {
            "string": str,
            "number": (int, float),
            "integer": int,
            "float": float,
            "boolean": bool,
            "object": object,
            "array": list,
            "any": object,
        }
        
        expected_type = type_mapping.get(self.type.lower(), object)
        return isinstance(value, expected_type)


class NodeInputPort(BaseModel):
    """节点输入端口
    
    定义节点的输入连接点，用于工作流中的节点连接。
    每个端口代表一个独立的输入来源。
    
    Attributes:
        name: 端口名称（唯一标识）
        label: 端口显示标签
        schemas: 该端口接受的输入模式列表
        required: 是否为必需端口
        multiple: 是否允许多个输入连接
        
    Example:
        >>> port = NodeInputPort(
        ...     name="data",
        ...     label="数据输入",
        ...     required=True,
        ...     schemas=[
        ...         NodeInputSchema(name="query", type="string", required=True)
        ...     ]
        ... )
    """
    
    model_config = ConfigDict(extra="allow")
    
    name: str = Field(
        description="端口名称（唯一标识）"
    )
    label: str = Field(
        default="",
        description="端口显示标签"
    )
    schemas: List[NodeInputSchema] = Field(
        default_factory=list,
        description="该端口接受的输入模式列表"
    )
    required: bool = Field(
        default=True,
        description="是否为必需端口（如果为True，执行时必须提供此端口的输入）"
    )
    multiple: bool = Field(
        default=False,
        description="是否允许多个输入连接（用于未来扩展）"
    )
    
    def validate_input(self, input_data: NodeInput) -> tuple[bool, List[str]]:
        """验证输入数据是否符合端口要求
        
        Args:
            input_data: 输入数据
            
        Returns:
            (是否验证通过, 错误信息列表)
        """
        errors = []
        
        for schema in self.schemas:
            value = input_data.get(schema.name, schema.default)
            
            if not schema.validate_value(value):
                if schema.required:
                    errors.append(
                        f"必需参数 '{schema.name}' 缺失或类型错误，期望类型: {schema.type}"
                    )
                else:
                    errors.append(
                        f"可选参数 '{schema.name}' 类型错误，期望类型: {schema.type}"
                    )
        
        return len(errors) == 0, errors


