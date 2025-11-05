"""节点输出定义

定义节点产生的输出数据结构。
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, ConfigDict
from enum import Enum


class NodeStatus(str, Enum):
    """节点执行状态"""
    
    PENDING = "pending"        # 待执行
    RUNNING = "running"        # 执行中
    SUCCESS = "success"        # 执行成功
    FAILED = "failed"          # 执行失败
    SKIPPED = "skipped"        # 跳过执行
    CANCELLED = "cancelled"    # 已取消


class NodeOutput(BaseModel):
    """节点输出数据模型
    
    节点执行后产生的输出数据结构。
    
    Attributes:
        data: 主要输出数据
        metadata: 输出元数据
        status: 节点执行状态
        error: 错误信息（如果执行失败）
        logs: 执行日志
        metrics: 执行指标（如执行时间、token消耗等）
        
    Example:
        >>> output = NodeOutput(
        ...     data={"result": [1, 2, 3]},
        ...     status=NodeStatus.SUCCESS,
        ...     metadata={"row_count": 3}
        ... )
    """
    
    model_config = ConfigDict(arbitrary_types_allowed=True, extra="allow")
    
    data: Any = Field(
        default=None,
        description="节点的主要输出数据"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="输出数据的元数据信息"
    )
    status: NodeStatus = Field(
        default=NodeStatus.SUCCESS,
        description="节点执行状态"
    )
    error: Optional[str] = Field(
        default=None,
        description="错误信息（如果执行失败）"
    )
    logs: List[str] = Field(
        default_factory=list,
        description="执行日志"
    )
    metrics: Dict[str, Any] = Field(
        default_factory=dict,
        description="执行指标，如执行时间、资源消耗等"
    )
    
    def is_success(self) -> bool:
        """判断节点是否执行成功
        
        Returns:
            是否执行成功
        """
        return self.status == NodeStatus.SUCCESS
    
    def is_failed(self) -> bool:
        """判断节点是否执行失败
        
        Returns:
            是否执行失败
        """
        return self.status == NodeStatus.FAILED
    
    def add_log(self, message: str) -> None:
        """添加日志信息
        
        Args:
            message: 日志消息
        """
        self.logs.append(message)
    
    def set_error(self, error: str) -> None:
        """设置错误信息并标记为失败状态
        
        Args:
            error: 错误信息
        """
        self.error = error
        self.status = NodeStatus.FAILED
    
    def set_metric(self, key: str, value: Any) -> None:
        """设置执行指标
        
        Args:
            key: 指标名称
            value: 指标值
            
        Example:
            >>> output = NodeOutput()
            >>> output.set_metric("duration_ms", 1250)
            >>> output.set_metric("tokens_used", 450)
        """
        self.metrics[key] = value
    
    def get_metric(self, key: str, default: Any = None) -> Any:
        """获取执行指标
        
        Args:
            key: 指标名称
            default: 默认值
            
        Returns:
            指标值
        """
        return self.metrics.get(key, default)


class NodeOutputSchema(BaseModel):
    """节点输出模式定义
    
    定义节点输出的数据结构和说明。
    
    Attributes:
        name: 输出参数名称
        type: 输出参数类型
        description: 参数描述
        
    Example:
        >>> schema = NodeOutputSchema(
        ...     name="result",
        ...     type="array",
        ...     description="查询结果集"
        ... )
    """
    
    model_config = ConfigDict(extra="allow")
    
    name: str = Field(
        description="输出参数名称"
    )
    type: str = Field(
        default="any",
        description="输出参数类型"
    )
    description: str = Field(
        default="",
        description="参数描述"
    )


class NodeOutputPort(BaseModel):
    """节点输出端口
    
    定义节点的输出连接点，用于工作流中的节点连接。
    
    Attributes:
        name: 端口名称
        label: 端口显示标签
        schemas: 该端口输出的数据模式列表
        
    Example:
        >>> port = NodeOutputPort(
        ...     name="result",
        ...     label="查询结果",
        ...     schemas=[
        ...         NodeOutputSchema(name="data", type="array", description="结果数据")
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
    schemas: List[NodeOutputSchema] = Field(
        default_factory=list,
        description="该端口输出的数据模式列表"
    )


