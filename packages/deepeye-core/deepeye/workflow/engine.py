"""工作流引擎模块

提供完整的工作流管理功能，包括创建、验证、序列化等。
"""

import json
import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional, TYPE_CHECKING
from pathlib import Path
from pydantic import BaseModel, Field

from deepeye.workflow.graph import WorkflowGraph, NodeConnection
from deepeye.workflow.validator import WorkflowValidator
from deepeye.nodes import BaseNode
from deepeye.exceptions import WorkflowError

if TYPE_CHECKING:
    from deepeye.runtime.context import ExecutionContext


class WorkflowMetadata(BaseModel):
    """工作流元数据
    
    Attributes:
        name: 工作流名称
        description: 工作流描述
        version: 工作流版本
        author: 作者
        created_at: 创建时间
        updated_at: 更新时间
        tags: 标签列表
    """
    name: str
    description: str = ""
    version: str = "1.0.0"
    author: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    tags: List[str] = Field(default_factory=list)


class Workflow:
    """工作流主类
    
    整合图、构建器、验证器，提供完整的工作流管理功能。
    
    Attributes:
        workflow_id: 工作流唯一标识符
        metadata: 工作流元数据
        graph: 工作流图
        nodes: 节点实例字典
        
    Example:
        >>> workflow = Workflow(name="数据分析工作流")
        >>> workflow.add_node("data", DataSourceNode())
        >>> workflow.add_node("sql", NL2SQLNode())
        >>> workflow.connect("data", "sql")
        >>> workflow.validate()
        >>> workflow.save("workflow.json")
    """
    
    def __init__(
        self,
        name: str,
        description: str = "",
        workflow_id: Optional[str] = None,
        metadata: Optional[WorkflowMetadata] = None
    ) -> None:
        """初始化工作流
        
        Args:
            name: 工作流名称
            description: 工作流描述
            workflow_id: 工作流ID（可选，默认自动生成）
            metadata: 工作流元数据（可选）
        """
        self.workflow_id = workflow_id or str(uuid.uuid4())
        
        if metadata is None:
            self.metadata = WorkflowMetadata(
                name=name,
                description=description
            )
        else:
            self.metadata = metadata
        
        self.graph = WorkflowGraph()
        self.nodes: Dict[str, BaseNode] = {}
        self._validator = WorkflowValidator()
    
    # ========== 节点管理 ==========
    
    def add_node(
        self,
        node_id: str,
        node: BaseNode,
        **node_metadata: Any
    ) -> "Workflow":
        """添加节点
        
        Args:
            node_id: 节点唯一标识符
            node: 节点实例
            **node_metadata: 节点元数据
            
        Returns:
            工作流自身（支持链式调用）
            
        Raises:
            WorkflowError: 如果节点ID已存在
        """
        if node_id in self.nodes:
            raise WorkflowError(f"节点ID '{node_id}' 已存在")
        
        # 添加到图
        graph_data = {
            "node_type": node.node_type,
            "metadata": node_metadata
        }
        self.graph.add_node(node_id, graph_data)
        
        # 保存节点实例
        self.nodes[node_id] = node
        
        # 更新时间戳
        self.metadata.updated_at = datetime.now()
        
        return self
    
    def get_node(self, node_id: str) -> BaseNode:
        """获取节点实例
        
        Args:
            node_id: 节点ID
            
        Returns:
            节点实例
            
        Raises:
            WorkflowError: 如果节点不存在
        """
        if node_id not in self.nodes:
            raise WorkflowError(f"节点ID '{node_id}' 不存在")
        return self.nodes[node_id]
    
    def remove_node(self, node_id: str) -> "Workflow":
        """删除节点
        
        Args:
            node_id: 节点ID
            
        Returns:
            工作流自身（支持链式调用）
        """
        if node_id not in self.nodes:
            raise WorkflowError(f"节点ID '{node_id}' 不存在")
        
        # 从图中删除
        self.graph.remove_node(node_id)
        
        # 删除节点实例
        del self.nodes[node_id]
        
        # 更新时间戳
        self.metadata.updated_at = datetime.now()
        
        return self
    
    def list_nodes(self) -> List[str]:
        """列出所有节点ID
        
        Returns:
            节点ID列表
        """
        return list(self.nodes.keys())
    
    def has_node(self, node_id: str) -> bool:
        """检查节点是否存在
        
        Args:
            node_id: 节点ID
            
        Returns:
            节点是否存在
        """
        return node_id in self.nodes
    
    # ========== 连接管理 ==========
    
    def add_connection(
        self,
        from_node_id: str,
        to_node_id: str,
        from_port: Optional[str] = None,
        to_port: Optional[str] = None
    ) -> "Workflow":
        """添加连接（connect的别名）
        
        Args:
            from_node_id: 源节点ID
            to_node_id: 目标节点ID
            from_port: 源节点输出端口名称（可选）
            to_port: 目标节点输入端口名称（可选）
            
        Returns:
            工作流自身（支持链式调用）
        """
        return self.connect(from_node_id, to_node_id, from_port, to_port)
    
    def connect(
        self,
        from_node_id: str,
        to_node_id: str,
        from_port: Optional[str] = None,
        to_port: Optional[str] = None
    ) -> "Workflow":
        """连接两个节点
        
        Args:
            from_node_id: 源节点ID
            to_node_id: 目标节点ID
            from_port: 源节点输出端口名称（可选）
            to_port: 目标节点输入端口名称（可选）
            
        Returns:
            工作流自身（支持链式调用）
        """
        if from_node_id not in self.nodes:
            raise WorkflowError(f"源节点 '{from_node_id}' 不存在")
        if to_node_id not in self.nodes:
            raise WorkflowError(f"目标节点 '{to_node_id}' 不存在")
        
        from_node = self.nodes[from_node_id]
        to_node = self.nodes[to_node_id]
        
        # 如果未指定端口，使用默认端口
        if from_port is None:
            if not from_node.output_ports:
                raise WorkflowError(f"节点 '{from_node_id}' 没有输出端口")
            from_port = from_node.output_ports[0].name
        
        if to_port is None:
            if not to_node.input_ports:
                raise WorkflowError(f"节点 '{to_node_id}' 没有输入端口")
            to_port = to_node.input_ports[0].name
        
        # 创建连接
        connection = NodeConnection(
            from_node_id=from_node_id,
            from_port=from_port,
            to_node_id=to_node_id,
            to_port=to_port
        )
        
        self.graph.add_edge(from_node_id, to_node_id, connection)
        
        # 更新时间戳
        self.metadata.updated_at = datetime.now()
        
        return self
    
    def connect_ports(
        self,
        from_node_id: str,
        from_port: str,
        to_node_id: str,
        to_port: str
    ) -> "Workflow":
        """精确指定端口进行连接（connect的别名方法）
        
        这是 connect() 的便捷方法，参数顺序更明确。
        
        Args:
            from_node_id: 源节点ID
            from_port: 源节点的输出端口名称
            to_node_id: 目标节点ID
            to_port: 目标节点的输入端口名称
            
        Returns:
            工作流自身（支持链式调用）
        """
        return self.connect(from_node_id, to_node_id, from_port, to_port)
    
    def remove_connection(
        self,
        from_node_id: str,
        to_node_id: str
    ) -> "Workflow":
        """删除连接
        
        Args:
            from_node_id: 源节点ID
            to_node_id: 目标节点ID
            
        Returns:
            工作流自身（支持链式调用）
        """
        self.graph.remove_edge(from_node_id, to_node_id)
        
        # 更新时间戳
        self.metadata.updated_at = datetime.now()
        
        return self
    
    def get_connections(self) -> List[NodeConnection]:
        """获取所有连接
        
        Returns:
            连接列表
        """
        connections = []
        for from_id, to_id in self.graph.list_edges():
            conn = self.graph.get_edge(from_id, to_id)
            connections.append(conn)
        return connections
    
    # ========== 验证 ==========
    
    def validate(
        self,
        raise_on_error: bool = False,
        context: Optional["ExecutionContext"] = None
    ) -> bool:
        """验证工作流
        
        Args:
            raise_on_error: 如果为True，验证失败时抛出异常
            context: 执行上下文（可选，用于检查静态输入）
            
        Returns:
            是否验证通过
        """
        if raise_on_error:
            self._validator.validate_and_raise(self.graph, self.nodes, context)
            return True
        else:
            report = self._validator.validate(self.graph, self.nodes, context)
            return report.is_valid
    
    def is_valid(self, context: Optional["ExecutionContext"] = None) -> bool:
        """检查工作流是否有效
        
        Args:
            context: 执行上下文（可选，用于检查静态输入）
        
        Returns:
            是否有效
        """
        return self.validate(context=context)
    
    def get_validation_report(self, context: Optional["ExecutionContext"] = None):
        """获取验证报告
        
        Args:
            context: 执行上下文（可选，用于检查静态输入）
        
        Returns:
            ValidationReport 对象
        """
        return self._validator.validate(self.graph, self.nodes, context)
    
    # ========== 序列化 ==========
    
    def to_dict(self) -> Dict[str, Any]:
        """导出为字典
        
        Returns:
            工作流的字典表示
            
        Note:
            节点实例不会被序列化，只保存节点类型和配置。
            要完全恢复工作流，需要节点注册表支持。
        """
        # 导出图结构
        graph_dict = self.graph.to_dict()
        
        # 导出节点配置
        nodes_data = {}
        for node_id, node in self.nodes.items():
            # 使用 model_dump 替代 dict()
            config_dict = node.config.model_dump() if node.config else {}
            metadata_dict = node.metadata.model_dump() if node.metadata else {}
            
            nodes_data[node_id] = {
                "node_type": node.node_type,
                "node_id": node.node_id,
                "config": config_dict,
                "metadata": metadata_dict
            }
        
        # 导出元数据，手动转换 datetime
        metadata_dict = self.metadata.model_dump()
        metadata_dict["created_at"] = self.metadata.created_at.isoformat()
        metadata_dict["updated_at"] = self.metadata.updated_at.isoformat()
        
        return {
            "workflow_id": self.workflow_id,
            "metadata": metadata_dict,
            "graph": graph_dict,
            "nodes": nodes_data
        }
    
    def to_json(self, indent: int = 2) -> str:
        """导出为JSON字符串
        
        Args:
            indent: JSON缩进空格数
            
        Returns:
            JSON字符串
        """
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)
    
    def save(self, filepath: str) -> None:
        """保存工作流到文件
        
        Args:
            filepath: 文件路径
        """
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(path, "w", encoding="utf-8") as f:
            f.write(self.to_json())
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any], node_registry=None) -> "Workflow":
        """从字典创建工作流
        
        Args:
            data: 工作流字典
            node_registry: 节点注册表（用于创建节点实例）
            
        Returns:
            Workflow 实例
            
        Note:
            如果提供了 node_registry，将尝试从注册表创建节点实例。
            否则，需要手动添加节点实例。
        """
        # 创建元数据
        metadata = WorkflowMetadata(**data["metadata"])
        
        # 创建工作流
        workflow = cls(
            name=metadata.name,
            description=metadata.description,
            workflow_id=data["workflow_id"],
            metadata=metadata
        )
        
        # 如果提供了节点注册表，创建节点实例
        if node_registry is not None:
            from deepeye.nodes import NodeConfig
            
            for node_id, node_data in data["nodes"].items():
                # 从注册表创建节点
                config = NodeConfig(**node_data["config"]) if node_data["config"] else None
                node = node_registry.create_node(
                    node_data["node_type"],
                    node_id=node_id,
                    config=config
                )
                
                # 添加节点（不通过 add_node 以避免重新创建图节点）
                workflow.nodes[node_id] = node
        
        # 恢复图结构
        workflow.graph = WorkflowGraph.from_dict(data["graph"])
        
        return workflow
    
    @classmethod
    def from_json(cls, json_str: str, node_registry=None) -> "Workflow":
        """从JSON字符串创建工作流
        
        Args:
            json_str: JSON字符串
            node_registry: 节点注册表
            
        Returns:
            Workflow 实例
        """
        data = json.loads(json_str)
        return cls.from_dict(data, node_registry)
    
    @classmethod
    def load(cls, filepath: str, node_registry=None) -> "Workflow":
        """从文件加载工作流
        
        Args:
            filepath: 文件路径
            node_registry: 节点注册表
            
        Returns:
            Workflow 实例
        """
        with open(filepath, "r", encoding="utf-8") as f:
            return cls.from_json(f.read(), node_registry)
    
    # ========== 信息查询 ==========
    
    def get_execution_order(self) -> List[str]:
        """获取执行顺序（拓扑排序）
        
        Returns:
            节点ID列表（按执行顺序）
        """
        return self.graph.get_topological_order()
    
    def get_node_dependencies(self, node_id: str) -> List[str]:
        """获取节点的依赖节点（前驱）
        
        Args:
            node_id: 节点ID
            
        Returns:
            依赖节点ID列表
        """
        return self.graph.get_predecessors(node_id)
    
    def get_node_dependents(self, node_id: str) -> List[str]:
        """获取依赖此节点的节点（后继）
        
        Args:
            node_id: 节点ID
            
        Returns:
            依赖节点ID列表
        """
        return self.graph.get_successors(node_id)
    
    def get_execution_layers(self) -> List[List[str]]:
        """获取执行层级（可并行执行的节点分组）
        
        Returns:
            层级列表，每层是一个节点ID列表
        """
        return self.graph.get_execution_layers()
    
    def get_root_nodes(self) -> List[str]:
        """获取根节点（没有输入的节点）
        
        Returns:
            根节点ID列表
        """
        return self.graph.get_root_nodes()
    
    def get_leaf_nodes(self) -> List[str]:
        """获取叶子节点（没有输出的节点）
        
        Returns:
            叶子节点ID列表
        """
        return self.graph.get_leaf_nodes()
    
    def clear(self) -> "Workflow":
        """清空工作流
        
        清空所有节点和连接，重置为初始状态。
        保留工作流ID和元数据。
        
        Returns:
            工作流自身（支持链式调用）
        """
        self.graph = WorkflowGraph()
        self.nodes = {}
        self.metadata.updated_at = datetime.now()
        return self
    
    def __repr__(self) -> str:
        """字符串表示"""
        return (
            f"Workflow("
            f"id='{self.workflow_id[:8]}...', "
            f"name='{self.metadata.name}', "
            f"nodes={len(self.nodes)}, "
            f"connections={self.graph.edge_count()})"
        )

