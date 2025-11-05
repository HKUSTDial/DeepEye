"""测试工作流图结构"""

import pytest
from deepeye.workflow.graph import WorkflowGraph, NodeConnection
from deepeye.exceptions import (
    WorkflowError,
    NodeNotFoundError,
    WorkflowValidationError,
)


class TestNodeConnection:
    """测试节点连接"""
    
    def test_create_connection(self):
        """测试创建连接"""
        conn = NodeConnection(
            from_node_id="node1",
            from_port="output",
            to_node_id="node2",
            to_port="input"
        )
        
        assert conn.from_node_id == "node1"
        assert conn.from_port == "output"
        assert conn.to_node_id == "node2"
        assert conn.to_port == "input"
        assert conn.metadata == {}
    
    def test_connection_with_metadata(self):
        """测试带元数据的连接"""
        conn = NodeConnection(
            from_node_id="node1",
            from_port="output",
            to_node_id="node2",
            to_port="input",
            metadata={"type": "data"}
        )
        
        assert conn.metadata == {"type": "data"}
    
    def test_connection_to_dict(self):
        """测试连接转换为字典"""
        conn = NodeConnection(
            from_node_id="node1",
            from_port="output",
            to_node_id="node2",
            to_port="input",
            metadata={"type": "data"}
        )
        
        data = conn.to_dict()
        assert data["from_node_id"] == "node1"
        assert data["from_port"] == "output"
        assert data["to_node_id"] == "node2"
        assert data["to_port"] == "input"
        assert data["metadata"] == {"type": "data"}
    
    def test_connection_from_dict(self):
        """测试从字典创建连接"""
        data = {
            "from_node_id": "node1",
            "from_port": "output",
            "to_node_id": "node2",
            "to_port": "input",
            "metadata": {"type": "data"}
        }
        
        conn = NodeConnection.from_dict(data)
        assert conn.from_node_id == "node1"
        assert conn.from_port == "output"
        assert conn.to_node_id == "node2"
        assert conn.to_port == "input"
        assert conn.metadata == {"type": "data"}


class TestWorkflowGraph:
    """测试工作流图"""
    
    def test_create_empty_graph(self):
        """测试创建空图"""
        graph = WorkflowGraph()
        
        assert graph.is_empty()
        assert graph.node_count() == 0
        assert graph.edge_count() == 0
        assert graph.is_dag()
    
    def test_add_node(self):
        """测试添加节点"""
        graph = WorkflowGraph()
        graph.add_node("node1", {"type": "DataSource"})
        
        assert graph.has_node("node1")
        assert graph.node_count() == 1
        assert not graph.is_empty()
        
        node_data = graph.get_node("node1")
        assert node_data["type"] == "DataSource"
    
    def test_add_duplicate_node_raises_error(self):
        """测试添加重复节点抛出异常"""
        graph = WorkflowGraph()
        graph.add_node("node1")
        
        with pytest.raises(WorkflowError, match="已存在"):
            graph.add_node("node1")
    
    def test_remove_node(self):
        """测试删除节点"""
        graph = WorkflowGraph()
        graph.add_node("node1")
        graph.add_node("node2")
        
        graph.remove_node("node1")
        
        assert not graph.has_node("node1")
        assert graph.has_node("node2")
        assert graph.node_count() == 1
    
    def test_remove_nonexistent_node_raises_error(self):
        """测试删除不存在的节点抛出异常"""
        graph = WorkflowGraph()
        
        with pytest.raises(NodeNotFoundError, match="不存在"):
            graph.remove_node("node1")
    
    def test_update_node(self):
        """测试更新节点数据"""
        graph = WorkflowGraph()
        graph.add_node("node1", {"type": "DataSource"})
        
        graph.update_node("node1", {"type": "NL2SQL", "config": {"model": "gpt-4"}})
        
        node_data = graph.get_node("node1")
        assert node_data["type"] == "NL2SQL"
        assert node_data["config"] == {"model": "gpt-4"}
    
    def test_list_nodes(self):
        """测试列出所有节点"""
        graph = WorkflowGraph()
        graph.add_node("node1")
        graph.add_node("node2")
        graph.add_node("node3")
        
        nodes = graph.list_nodes()
        assert len(nodes) == 3
        assert "node1" in nodes
        assert "node2" in nodes
        assert "node3" in nodes
    
    def test_add_edge(self):
        """测试添加边"""
        graph = WorkflowGraph()
        graph.add_node("node1")
        graph.add_node("node2")
        
        conn = NodeConnection("node1", "output", "node2", "input")
        graph.add_edge("node1", "node2", conn)
        
        assert graph.has_edge("node1", "node2")
        assert graph.edge_count() == 1
    
    def test_add_edge_with_nonexistent_nodes_raises_error(self):
        """测试连接不存在的节点抛出异常"""
        graph = WorkflowGraph()
        graph.add_node("node1")
        
        conn = NodeConnection("node1", "output", "node2", "input")
        
        with pytest.raises(NodeNotFoundError, match="不存在"):
            graph.add_edge("node1", "node2", conn)
    
    def test_add_duplicate_edge_raises_error(self):
        """测试添加重复边抛出异常"""
        graph = WorkflowGraph()
        graph.add_node("node1")
        graph.add_node("node2")
        
        conn = NodeConnection("node1", "output", "node2", "input")
        graph.add_edge("node1", "node2", conn)
        
        with pytest.raises(WorkflowError, match="已存在"):
            graph.add_edge("node1", "node2", conn)
    
    def test_remove_edge(self):
        """测试删除边"""
        graph = WorkflowGraph()
        graph.add_node("node1")
        graph.add_node("node2")
        
        conn = NodeConnection("node1", "output", "node2", "input")
        graph.add_edge("node1", "node2", conn)
        
        graph.remove_edge("node1", "node2")
        
        assert not graph.has_edge("node1", "node2")
        assert graph.edge_count() == 0
    
    def test_get_edge(self):
        """测试获取边数据"""
        graph = WorkflowGraph()
        graph.add_node("node1")
        graph.add_node("node2")
        
        conn = NodeConnection("node1", "output", "node2", "input")
        graph.add_edge("node1", "node2", conn)
        
        retrieved_conn = graph.get_edge("node1", "node2")
        assert retrieved_conn.from_node_id == "node1"
        assert retrieved_conn.from_port == "output"
        assert retrieved_conn.to_node_id == "node2"
        assert retrieved_conn.to_port == "input"
    
    def test_list_edges(self):
        """测试列出所有边"""
        graph = WorkflowGraph()
        graph.add_node("node1")
        graph.add_node("node2")
        graph.add_node("node3")
        
        conn1 = NodeConnection("node1", "output", "node2", "input")
        conn2 = NodeConnection("node2", "output", "node3", "input")
        graph.add_edge("node1", "node2", conn1)
        graph.add_edge("node2", "node3", conn2)
        
        edges = graph.list_edges()
        assert len(edges) == 2
        assert ("node1", "node2") in edges
        assert ("node2", "node3") in edges
    
    def test_get_predecessors(self):
        """测试获取前驱节点"""
        graph = WorkflowGraph()
        graph.add_node("node1")
        graph.add_node("node2")
        graph.add_node("node3")
        
        conn1 = NodeConnection("node1", "output", "node3", "input1")
        conn2 = NodeConnection("node2", "output", "node3", "input2")
        graph.add_edge("node1", "node3", conn1)
        graph.add_edge("node2", "node3", conn2)
        
        predecessors = graph.get_predecessors("node3")
        assert len(predecessors) == 2
        assert "node1" in predecessors
        assert "node2" in predecessors
    
    def test_get_successors(self):
        """测试获取后继节点"""
        graph = WorkflowGraph()
        graph.add_node("node1")
        graph.add_node("node2")
        graph.add_node("node3")
        
        conn1 = NodeConnection("node1", "output", "node2", "input")
        conn2 = NodeConnection("node1", "output", "node3", "input")
        graph.add_edge("node1", "node2", conn1)
        graph.add_edge("node1", "node3", conn2)
        
        successors = graph.get_successors("node1")
        assert len(successors) == 2
        assert "node2" in successors
        assert "node3" in successors
    
    def test_get_root_nodes(self):
        """测试获取根节点"""
        graph = WorkflowGraph()
        graph.add_node("node1")
        graph.add_node("node2")
        graph.add_node("node3")
        
        conn1 = NodeConnection("node1", "output", "node3", "input")
        conn2 = NodeConnection("node2", "output", "node3", "input")
        graph.add_edge("node1", "node3", conn1)
        graph.add_edge("node2", "node3", conn2)
        
        roots = graph.get_root_nodes()
        assert len(roots) == 2
        assert "node1" in roots
        assert "node2" in roots
        assert "node3" not in roots
    
    def test_get_leaf_nodes(self):
        """测试获取叶子节点"""
        graph = WorkflowGraph()
        graph.add_node("node1")
        graph.add_node("node2")
        graph.add_node("node3")
        
        conn1 = NodeConnection("node1", "output", "node2", "input")
        conn2 = NodeConnection("node1", "output", "node3", "input")
        graph.add_edge("node1", "node2", conn1)
        graph.add_edge("node1", "node3", conn2)
        
        leaves = graph.get_leaf_nodes()
        assert len(leaves) == 2
        assert "node2" in leaves
        assert "node3" in leaves
        assert "node1" not in leaves
    
    def test_is_dag(self):
        """测试 DAG 检测"""
        graph = WorkflowGraph()
        graph.add_node("node1")
        graph.add_node("node2")
        graph.add_node("node3")
        
        conn1 = NodeConnection("node1", "output", "node2", "input")
        conn2 = NodeConnection("node2", "output", "node3", "input")
        graph.add_edge("node1", "node2", conn1)
        graph.add_edge("node2", "node3", conn2)
        
        assert graph.is_dag()
        assert not graph.has_cycle()
    
    def test_cycle_detection(self):
        """测试循环检测"""
        graph = WorkflowGraph()
        graph.add_node("node1")
        graph.add_node("node2")
        graph.add_node("node3")
        
        conn1 = NodeConnection("node1", "output", "node2", "input")
        conn2 = NodeConnection("node2", "output", "node3", "input")
        graph.add_edge("node1", "node2", conn1)
        graph.add_edge("node2", "node3", conn2)
        
        # 尝试添加会形成循环的边
        conn3 = NodeConnection("node3", "output", "node1", "input")
        with pytest.raises(WorkflowError, match="循环依赖"):
            graph.add_edge("node3", "node1", conn3)
    
    def test_find_cycle(self):
        """测试查找循环路径"""
        graph = WorkflowGraph()
        graph.add_node("node1")
        graph.add_node("node2")
        
        # 无循环时返回 None
        assert graph.find_cycle() is None
    
    def test_topological_sort(self):
        """测试拓扑排序"""
        graph = WorkflowGraph()
        graph.add_node("node1")
        graph.add_node("node2")
        graph.add_node("node3")
        
        conn1 = NodeConnection("node1", "output", "node2", "input")
        conn2 = NodeConnection("node2", "output", "node3", "input")
        graph.add_edge("node1", "node2", conn1)
        graph.add_edge("node2", "node3", conn2)
        
        order = graph.get_topological_order()
        
        # 验证顺序正确
        assert order.index("node1") < order.index("node2")
        assert order.index("node2") < order.index("node3")
    
    def test_get_node_depth(self):
        """测试获取节点深度"""
        graph = WorkflowGraph()
        graph.add_node("node1")
        graph.add_node("node2")
        graph.add_node("node3")
        graph.add_node("node4")
        
        conn1 = NodeConnection("node1", "output", "node2", "input")
        conn2 = NodeConnection("node2", "output", "node3", "input")
        conn3 = NodeConnection("node3", "output", "node4", "input")
        graph.add_edge("node1", "node2", conn1)
        graph.add_edge("node2", "node3", conn2)
        graph.add_edge("node3", "node4", conn3)
        
        assert graph.get_node_depth("node1") == 0
        assert graph.get_node_depth("node2") == 1
        assert graph.get_node_depth("node3") == 2
        assert graph.get_node_depth("node4") == 3
    
    def test_get_execution_layers(self):
        """测试获取执行层级"""
        graph = WorkflowGraph()
        graph.add_node("node1")
        graph.add_node("node2")
        graph.add_node("node3")
        graph.add_node("node4")
        
        # node1 -> node2, node3
        # node2, node3 -> node4
        conn1 = NodeConnection("node1", "output", "node2", "input")
        conn2 = NodeConnection("node1", "output", "node3", "input")
        conn3 = NodeConnection("node2", "output", "node4", "input")
        conn4 = NodeConnection("node3", "output", "node4", "input")
        graph.add_edge("node1", "node2", conn1)
        graph.add_edge("node1", "node3", conn2)
        graph.add_edge("node2", "node4", conn3)
        graph.add_edge("node3", "node4", conn4)
        
        layers = graph.get_execution_layers()
        
        assert len(layers) == 3
        assert layers[0] == ["node1"]
        assert set(layers[1]) == {"node2", "node3"}
        assert layers[2] == ["node4"]
    
    def test_validate(self):
        """测试图验证"""
        graph = WorkflowGraph()
        graph.add_node("node1")
        graph.add_node("node2")
        
        conn = NodeConnection("node1", "output", "node2", "input")
        graph.add_edge("node1", "node2", conn)
        
        # 应该不抛出异常
        graph.validate()
    
    def test_to_dict(self):
        """测试转换为字典"""
        graph = WorkflowGraph()
        graph.add_node("node1", {"type": "DataSource"})
        graph.add_node("node2", {"type": "NL2SQL"})
        
        conn = NodeConnection("node1", "output", "node2", "input")
        graph.add_edge("node1", "node2", conn)
        
        data = graph.to_dict()
        
        assert "nodes" in data
        assert "edges" in data
        assert len(data["nodes"]) == 2
        assert len(data["edges"]) == 1
        
        # 验证节点数据
        node_ids = [n["id"] for n in data["nodes"]]
        assert "node1" in node_ids
        assert "node2" in node_ids
        
        # 验证边数据
        edge = data["edges"][0]
        assert edge["from_node_id"] == "node1"
        assert edge["to_node_id"] == "node2"
    
    def test_from_dict(self):
        """测试从字典创建"""
        data = {
            "nodes": [
                {"id": "node1", "data": {"type": "DataSource"}},
                {"id": "node2", "data": {"type": "NL2SQL"}},
            ],
            "edges": [
                {
                    "from_node_id": "node1",
                    "from_port": "output",
                    "to_node_id": "node2",
                    "to_port": "input",
                    "metadata": {}
                }
            ]
        }
        
        graph = WorkflowGraph.from_dict(data)
        
        assert graph.node_count() == 2
        assert graph.edge_count() == 1
        assert graph.has_node("node1")
        assert graph.has_node("node2")
        assert graph.has_edge("node1", "node2")
    
    def test_repr(self):
        """测试字符串表示"""
        graph = WorkflowGraph()
        graph.add_node("node1")
        graph.add_node("node2")
        
        conn = NodeConnection("node1", "output", "node2", "input")
        graph.add_edge("node1", "node2", conn)
        
        repr_str = repr(graph)
        assert "WorkflowGraph" in repr_str
        assert "nodes=2" in repr_str
        assert "edges=1" in repr_str
        assert "is_dag=True" in repr_str

