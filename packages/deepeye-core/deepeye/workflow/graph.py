"""工作流图结构模块

基于 NetworkX 实现的有向无环图(DAG)，用于表示工作流的节点依赖关系。
"""

from typing import Dict, List, Any, Optional, Set, Tuple
from dataclasses import dataclass, field
import networkx as nx
from pydantic import BaseModel, Field

from deepeye.exceptions import (
    WorkflowError,
    WorkflowValidationError,
    NodeNotFoundError,
)


@dataclass
class NodeConnection:
    """节点连接（边）
    
    表示从一个节点的输出端口到另一个节点的输入端口的连接。
    
    Attributes:
        from_node_id: 源节点 ID
        from_port: 源节点的输出端口名称
        to_node_id: 目标节点 ID
        to_port: 目标节点的输入端口名称
        metadata: 连接的元数据
        
    Example:
        >>> conn = NodeConnection(
        ...     from_node_id="node1",
        ...     from_port="output",
        ...     to_node_id="node2",
        ...     to_port="input"
        ... )
    """
    
    from_node_id: str
    from_port: str
    to_node_id: str
    to_port: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "from_node_id": self.from_node_id,
            "from_port": self.from_port,
            "to_node_id": self.to_node_id,
            "to_port": self.to_port,
            "metadata": self.metadata,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "NodeConnection":
        """从字典创建"""
        return cls(
            from_node_id=data["from_node_id"],
            from_port=data["from_port"],
            to_node_id=data["to_node_id"],
            to_port=data["to_port"],
            metadata=data.get("metadata", {}),
        )


class WorkflowGraph:
    """工作流图结构
    
    基于 NetworkX 的有向图实现，管理节点和边的关系。
    提供拓扑排序、循环检测等图算法功能。
    
    Attributes:
        graph: NetworkX 有向图对象
        
    Example:
        >>> graph = WorkflowGraph()
        >>> graph.add_node("node1", {"type": "DataSource"})
        >>> graph.add_node("node2", {"type": "NL2SQL"})
        >>> graph.add_edge("node1", "node2", NodeConnection(...))
        >>> order = graph.get_topological_order()
    """
    
    def __init__(self) -> None:
        """初始化工作流图"""
        self._graph = nx.DiGraph()
    
    def add_node(
        self,
        node_id: str,
        node_data: Optional[Dict[str, Any]] = None
    ) -> None:
        """添加节点
        
        Args:
            node_id: 节点唯一标识符
            node_data: 节点相关数据（如节点类型、配置等）
            
        Raises:
            WorkflowError: 如果节点已存在
            
        Example:
            >>> graph.add_node("node1", {"type": "DataSource", "config": {...}})
        """
        if self.has_node(node_id):
            raise WorkflowError(f"节点 '{node_id}' 已存在")
        
        self._graph.add_node(node_id, **(node_data or {}))
    
    def remove_node(self, node_id: str) -> None:
        """删除节点
        
        删除节点及其所有相关的连接。
        
        Args:
            node_id: 节点 ID
            
        Raises:
            NodeNotFoundError: 如果节点不存在
            
        Example:
            >>> graph.remove_node("node1")
        """
        if not self.has_node(node_id):
            raise NodeNotFoundError(f"节点 '{node_id}' 不存在")
        
        self._graph.remove_node(node_id)
    
    def has_node(self, node_id: str) -> bool:
        """检查节点是否存在
        
        Args:
            node_id: 节点 ID
            
        Returns:
            节点是否存在
        """
        return self._graph.has_node(node_id)
    
    def get_node(self, node_id: str) -> Dict[str, Any]:
        """获取节点数据
        
        Args:
            node_id: 节点 ID
            
        Returns:
            节点数据字典
            
        Raises:
            NodeNotFoundError: 如果节点不存在
        """
        if not self.has_node(node_id):
            raise NodeNotFoundError(f"节点 '{node_id}' 不存在")
        
        return dict(self._graph.nodes[node_id])
    
    def update_node(self, node_id: str, node_data: Dict[str, Any]) -> None:
        """更新节点数据
        
        Args:
            node_id: 节点 ID
            node_data: 新的节点数据
            
        Raises:
            NodeNotFoundError: 如果节点不存在
        """
        if not self.has_node(node_id):
            raise NodeNotFoundError(f"节点 '{node_id}' 不存在")
        
        self._graph.nodes[node_id].update(node_data)
    
    def list_nodes(self) -> List[str]:
        """列出所有节点 ID
        
        Returns:
            节点 ID 列表
        """
        return list(self._graph.nodes())
    
    def add_edge(
        self,
        from_node_id: str,
        to_node_id: str,
        connection: NodeConnection
    ) -> None:
        """添加边（连接）
        
        Args:
            from_node_id: 源节点 ID
            to_node_id: 目标节点 ID
            connection: 连接对象
            
        Raises:
            NodeNotFoundError: 如果任一节点不存在
            WorkflowError: 如果连接已存在或会形成循环
            
        Example:
            >>> conn = NodeConnection("node1", "output", "node2", "input")
            >>> graph.add_edge("node1", "node2", conn)
        """
        if not self.has_node(from_node_id):
            raise NodeNotFoundError(f"源节点 '{from_node_id}' 不存在")
        if not self.has_node(to_node_id):
            raise NodeNotFoundError(f"目标节点 '{to_node_id}' 不存在")
        
        if self.has_edge(from_node_id, to_node_id):
            raise WorkflowError(
                f"连接 '{from_node_id}' -> '{to_node_id}' 已存在"
            )
        
        # 检查是否会形成循环
        self._graph.add_edge(from_node_id, to_node_id, connection=connection)
        
        if not self.is_dag():
            # 回滚
            self._graph.remove_edge(from_node_id, to_node_id)
            raise WorkflowError(
                f"添加连接 '{from_node_id}' -> '{to_node_id}' 会形成循环依赖"
            )
    
    def remove_edge(self, from_node_id: str, to_node_id: str) -> None:
        """删除边（连接）
        
        Args:
            from_node_id: 源节点 ID
            to_node_id: 目标节点 ID
            
        Raises:
            WorkflowError: 如果连接不存在
        """
        if not self.has_edge(from_node_id, to_node_id):
            raise WorkflowError(
                f"连接 '{from_node_id}' -> '{to_node_id}' 不存在"
            )
        
        self._graph.remove_edge(from_node_id, to_node_id)
    
    def has_edge(self, from_node_id: str, to_node_id: str) -> bool:
        """检查边（连接）是否存在
        
        Args:
            from_node_id: 源节点 ID
            to_node_id: 目标节点 ID
            
        Returns:
            连接是否存在
        """
        return self._graph.has_edge(from_node_id, to_node_id)
    
    def get_edge(self, from_node_id: str, to_node_id: str) -> NodeConnection:
        """获取边（连接）数据
        
        Args:
            from_node_id: 源节点 ID
            to_node_id: 目标节点 ID
            
        Returns:
            连接对象
            
        Raises:
            WorkflowError: 如果连接不存在
        """
        if not self.has_edge(from_node_id, to_node_id):
            raise WorkflowError(
                f"连接 '{from_node_id}' -> '{to_node_id}' 不存在"
            )
        
        return self._graph.edges[from_node_id, to_node_id]["connection"]
    
    def get_connections(self) -> List[NodeConnection]:
        """获取所有连接对象
        
        Returns:
            所有连接对象的列表
        
        Example:
            >>> connections = graph.get_connections()
            >>> for conn in connections:
            ...     print(f"{conn.from_node_id} -> {conn.to_node_id}")
        """
        connections = []
        for from_node, to_node in self._graph.edges():
            connection = self._graph.edges[from_node, to_node].get("connection")
            if connection:
                connections.append(connection)
        return connections
    
    def list_edges(self) -> List[Tuple[str, str]]:
        """列出所有边
        
        Returns:
            边的列表，每个元素是 (from_node_id, to_node_id) 元组
        """
        return list(self._graph.edges())
    
    def get_predecessors(self, node_id: str) -> List[str]:
        """获取节点的所有前驱节点（输入节点）
        
        Args:
            node_id: 节点 ID
            
        Returns:
            前驱节点 ID 列表
            
        Raises:
            NodeNotFoundError: 如果节点不存在
        """
        if not self.has_node(node_id):
            raise NodeNotFoundError(f"节点 '{node_id}' 不存在")
        
        return list(self._graph.predecessors(node_id))
    
    def get_successors(self, node_id: str) -> List[str]:
        """获取节点的所有后继节点（输出节点）
        
        Args:
            node_id: 节点 ID
            
        Returns:
            后继节点 ID 列表
            
        Raises:
            NodeNotFoundError: 如果节点不存在
        """
        if not self.has_node(node_id):
            raise NodeNotFoundError(f"节点 '{node_id}' 不存在")
        
        return list(self._graph.successors(node_id))
    
    def get_root_nodes(self) -> List[str]:
        """获取所有根节点（没有输入的节点）
        
        Returns:
            根节点 ID 列表
        """
        return [
            node_id for node_id in self._graph.nodes()
            if self._graph.in_degree(node_id) == 0
        ]
    
    def get_leaf_nodes(self) -> List[str]:
        """获取所有叶子节点（没有输出的节点）
        
        Returns:
            叶子节点 ID 列表
        """
        return [
            node_id for node_id in self._graph.nodes()
            if self._graph.out_degree(node_id) == 0
        ]
    
    def is_dag(self) -> bool:
        """检查图是否为有向无环图(DAG)
        
        Returns:
            是否为 DAG
        """
        return nx.is_directed_acyclic_graph(self._graph)
    
    def has_cycle(self) -> bool:
        """检查图是否包含循环依赖
        
        Returns:
            是否包含循环
        """
        return not self.is_dag()
    
    def find_cycle(self) -> Optional[List[str]]:
        """查找图中的循环
        
        Returns:
            循环路径（节点 ID 列表），如果没有循环则返回 None
        """
        try:
            cycle = nx.find_cycle(self._graph, orientation="original")
            return [u for u, v, _ in cycle] + [cycle[0][1]]
        except nx.NetworkXNoCycle:
            return None
    
    def get_topological_order(self) -> List[str]:
        """获取拓扑排序顺序
        
        拓扑排序确保节点在其所有依赖节点之后执行。
        
        Returns:
            节点 ID 列表（拓扑排序顺序）
            
        Raises:
            WorkflowError: 如果图包含循环依赖
            
        Example:
            >>> order = graph.get_topological_order()
            >>> # order = ["node1", "node2", "node3"]
        """
        if not self.is_dag():
            cycle = self.find_cycle()
            raise WorkflowError(
                f"工作流包含循环依赖，无法进行拓扑排序。循环路径: {' -> '.join(cycle or [])}"
            )
        
        return list(nx.topological_sort(self._graph))
    
    def get_node_depth(self, node_id: str) -> int:
        """获取节点的深度（从根节点开始的最长路径长度）
        
        Args:
            node_id: 节点 ID
            
        Returns:
            节点深度（根节点深度为 0）
            
        Raises:
            NodeNotFoundError: 如果节点不存在
        """
        if not self.has_node(node_id):
            raise NodeNotFoundError(f"节点 '{node_id}' 不存在")
        
        # 如果是根节点，深度为 0
        if self._graph.in_degree(node_id) == 0:
            return 0
        
        # 递归计算最大前驱深度 + 1
        max_depth = 0
        for pred in self.get_predecessors(node_id):
            depth = self.get_node_depth(pred)
            max_depth = max(max_depth, depth)
        
        return max_depth + 1
    
    def get_execution_layers(self) -> List[List[str]]:
        """获取执行层级
        
        将节点按照深度分组，同一层级的节点可以并行执行。
        
        Returns:
            节点层级列表，每层是一个节点 ID 列表
            
        Example:
            >>> layers = graph.get_execution_layers()
            >>> # layers = [["node1"], ["node2", "node3"], ["node4"]]
        """
        if not self.is_dag():
            raise WorkflowError("工作流包含循环依赖，无法分层")
        
        # 计算每个节点的深度
        node_depths: Dict[str, int] = {}
        for node_id in self._graph.nodes():
            node_depths[node_id] = self.get_node_depth(node_id)
        
        # 按深度分组
        max_depth = max(node_depths.values()) if node_depths else -1
        layers: List[List[str]] = [[] for _ in range(max_depth + 1)]
        
        for node_id, depth in node_depths.items():
            layers[depth].append(node_id)
        
        return layers
    
    def node_count(self) -> int:
        """获取节点数量"""
        return self._graph.number_of_nodes()
    
    def edge_count(self) -> int:
        """获取边数量"""
        return self._graph.number_of_edges()
    
    def is_empty(self) -> bool:
        """检查图是否为空"""
        return self.node_count() == 0
    
    def validate(self) -> None:
        """验证图结构
        
        Raises:
            WorkflowValidationError: 如果验证失败
        """
        # 检查是否为 DAG
        if self.has_cycle():
            cycle = self.find_cycle()
            raise WorkflowValidationError(
                f"工作流包含循环依赖: {' -> '.join(cycle or [])}"
            )
    
    def to_dict(self) -> Dict[str, Any]:
        """导出为字典
        
        Returns:
            图的字典表示
        """
        nodes = []
        for node_id in self._graph.nodes():
            node_data = self.get_node(node_id)
            nodes.append({
                "id": node_id,
                "data": node_data,
            })
        
        edges = []
        for from_id, to_id in self._graph.edges():
            connection = self.get_edge(from_id, to_id)
            edges.append(connection.to_dict())
        
        return {
            "nodes": nodes,
            "edges": edges,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WorkflowGraph":
        """从字典创建图
        
        Args:
            data: 图的字典表示
            
        Returns:
            WorkflowGraph 实例
        """
        graph = cls()
        
        # 添加节点
        for node_dict in data.get("nodes", []):
            graph.add_node(node_dict["id"], node_dict.get("data"))
        
        # 添加边
        for edge_dict in data.get("edges", []):
            connection = NodeConnection.from_dict(edge_dict)
            graph.add_edge(
                connection.from_node_id,
                connection.to_node_id,
                connection
            )
        
        return graph
    
    def __repr__(self) -> str:
        """字符串表示"""
        return (
            f"WorkflowGraph("
            f"nodes={self.node_count()}, "
            f"edges={self.edge_count()}, "
            f"is_dag={self.is_dag()})"
        )

