"""执行上下文模块

管理工作流执行过程中的全局状态和数据。
"""

import uuid
from typing import Dict, Any, Optional
from datetime import datetime
from deepeye.nodes.io import NodeOutput


class ExecutionContext:
    """执行上下文
    
    管理工作流执行过程中的状态、变量和节点输出缓存。
    
    Attributes:
        workflow_id: 工作流ID
        execution_id: 执行ID（每次执行唯一）
        variables: 全局变量字典
        node_outputs: 节点输出缓存（node_id -> port_name -> NodeOutput）
        metadata: 额外的元数据
        created_at: 创建时间
        
    Example:
        >>> context = ExecutionContext(workflow_id="wf-123")
        >>> context.set_variable("user_id", 42)
        >>> context.set_node_outputs("node1", {"output": NodeOutput(...)})
        >>> output = context.get_node_output("node1", "output")
    """
    
    def __init__(
        self,
        workflow_id: str,
        execution_id: Optional[str] = None,
        variables: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """初始化执行上下文
        
        Args:
            workflow_id: 工作流ID
            execution_id: 执行ID（可选，默认自动生成）
            variables: 初始变量（可选）
            metadata: 元数据（可选）
        """
        self.workflow_id = workflow_id
        self.execution_id = execution_id or str(uuid.uuid4())
        self.variables: Dict[str, Any] = variables or {}
        self.node_outputs: Dict[str, Dict[str, NodeOutput]] = {}  # node_id -> port_name -> NodeOutput
        self.metadata: Dict[str, Any] = metadata or {}
        self.created_at = datetime.now()
    
    # ========== 节点输出管理 ==========
    
    def set_node_outputs(self, node_id: str, outputs: Dict[str, NodeOutput]) -> None:
        """设置节点所有端口的输出结果
        
        Args:
            node_id: 节点ID
            outputs: 端口名称到输出对象的映射
        """
        self.node_outputs[node_id] = outputs
    
    def get_node_outputs(self, node_id: str) -> Optional[Dict[str, NodeOutput]]:
        """获取节点所有端口的输出结果
        
        Args:
            node_id: 节点ID
            
        Returns:
            端口名称到输出对象的映射，如果不存在返回None
        """
        return self.node_outputs.get(node_id)
    
    def get_node_output(self, node_id: str, port_name: str) -> Optional[NodeOutput]:
        """获取节点指定端口的输出结果
        
        Args:
            node_id: 节点ID
            port_name: 端口名称
            
        Returns:
            节点输出对象，如果不存在返回None
        """
        if node_id in self.node_outputs:
            return self.node_outputs[node_id].get(port_name)
        return None
    
    def set_node_input(self, node_id: str, port_name: str, value: Any) -> None:
        """为节点的特定输入端口设置静态值
        
        在 Agentic 模式下，某些节点的输入可能是静态的（不来自其他节点的输出），
        需要提前在执行上下文中设置。这个方法使用特殊的命名约定来存储这些静态输入。
        
        Args:
            node_id: 节点ID
            port_name: 输入端口名称
            value: 静态输入值
        
        Example:
            >>> context.set_node_input("step1_nl2sql", "question", "查询销售额")
            >>> value = context.get_node_input("step1_nl2sql", "question")
        """
        key = f"__node_input__{node_id}__{port_name}"
        self.set_variable(key, value)
    
    def get_node_input(self, node_id: str, port_name: str, default: Any = None) -> Any:
        """获取节点输入端口的静态值
        
        Args:
            node_id: 节点ID
            port_name: 输入端口名称
            default: 默认值
            
        Returns:
            静态输入值，如果不存在返回默认值
        """
        key = f"__node_input__{node_id}__{port_name}"
        return self.get_variable(key, default)
    
    def has_node_input(self, node_id: str, port_name: str) -> bool:
        """检查节点输入端口是否有静态值
        
        Args:
            node_id: 节点ID
            port_name: 输入端口名称
            
        Returns:
            是否存在静态值
        """
        key = f"__node_input__{node_id}__{port_name}"
        return self.has_variable(key)
    
    def has_node_output(self, node_id: str, port_name: Optional[str] = None) -> bool:
        """检查节点是否有输出结果
        
        Args:
            node_id: 节点ID
            port_name: 端口名称（可选）。如果为None，检查节点是否有任何输出
            
        Returns:
            是否存在输出结果
        """
        if port_name is None:
            return node_id in self.node_outputs
        return (
            node_id in self.node_outputs and
            port_name in self.node_outputs[node_id]
        )
    
    def remove_node_output(self, node_id: str) -> None:
        """移除节点的所有输出结果
        
        Args:
            node_id: 节点ID
        """
        if node_id in self.node_outputs:
            del self.node_outputs[node_id]
    
    def clear_node_outputs(self) -> None:
        """清空所有节点输出"""
        self.node_outputs.clear()
    
    # ========== 变量管理 ==========
    
    def set_variable(self, key: str, value: Any) -> None:
        """设置变量
        
        Args:
            key: 变量名
            value: 变量值
        """
        self.variables[key] = value
    
    def get_variable(self, key: str, default: Any = None) -> Any:
        """获取变量
        
        Args:
            key: 变量名
            default: 默认值（如果变量不存在）
            
        Returns:
            变量值
        """
        return self.variables.get(key, default)
    
    def has_variable(self, key: str) -> bool:
        """检查变量是否存在
        
        Args:
            key: 变量名
            
        Returns:
            是否存在
        """
        return key in self.variables
    
    def remove_variable(self, key: str) -> None:
        """移除变量
        
        Args:
            key: 变量名
        """
        if key in self.variables:
            del self.variables[key]
    
    def clear_variables(self) -> None:
        """清空所有变量"""
        self.variables.clear()
    
    # ========== 元数据管理 ==========
    
    def set_metadata(self, key: str, value: Any) -> None:
        """设置元数据
        
        Args:
            key: 键
            value: 值
        """
        self.metadata[key] = value
    
    def get_metadata(self, key: str, default: Any = None) -> Any:
        """获取元数据
        
        Args:
            key: 键
            default: 默认值
            
        Returns:
            元数据值
        """
        return self.metadata.get(key, default)
    
    # ========== 工具方法 ==========
    
    def clear(self) -> None:
        """清空所有数据（保留IDs和创建时间）"""
        self.node_outputs.clear()
        self.variables.clear()
        self.metadata.clear()
    
    def clone(self) -> "ExecutionContext":
        """克隆上下文
        
        创建一个新的上下文实例，包含当前的所有数据。
        注意：这是浅拷贝。
        
        Returns:
            新的ExecutionContext实例
        """
        new_context = ExecutionContext(
            workflow_id=self.workflow_id,
            execution_id=str(uuid.uuid4()),  # 新的执行ID
            variables=self.variables.copy(),
            metadata=self.metadata.copy()
        )
        new_context.node_outputs = self.node_outputs.copy()
        return new_context
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典
        
        Returns:
            字典表示
        """
        return {
            "workflow_id": self.workflow_id,
            "execution_id": self.execution_id,
            "variables": self.variables,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
            "node_outputs": {
                node_id: {
                    port_name: output.model_dump()
                    for port_name, output in outputs.items()
                }
                for node_id, outputs in self.node_outputs.items()
            }
        }
    
    def __repr__(self) -> str:
        """字符串表示"""
        return (
            f"ExecutionContext("
            f"workflow_id='{self.workflow_id}', "
            f"execution_id='{self.execution_id[:8]}...', "
            f"nodes={len(self.node_outputs)}, "
            f"vars={len(self.variables)})"
        )

