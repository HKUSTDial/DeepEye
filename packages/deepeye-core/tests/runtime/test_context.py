"""ExecutionContext 测试"""

import pytest
from deepeye.runtime.context import ExecutionContext
from deepeye.nodes.io import NodeOutput


class TestExecutionContext:
    """ExecutionContext 测试类"""
    
    def test_init_default(self):
        """测试默认初始化"""
        context = ExecutionContext(workflow_id="wf-123")
        
        assert context.workflow_id == "wf-123"
        assert context.execution_id is not None
        assert len(context.variables) == 0
        assert len(context.node_outputs) == 0
        assert len(context.metadata) == 0
        assert context.created_at is not None
    
    def test_init_with_params(self):
        """测试带参数初始化"""
        context = ExecutionContext(
            workflow_id="wf-123",
            execution_id="exec-456",
            variables={"key": "value"},
            metadata={"author": "test"}
        )
        
        assert context.workflow_id == "wf-123"
        assert context.execution_id == "exec-456"
        assert context.variables["key"] == "value"
        assert context.metadata["author"] == "test"
    
    # ========== 节点输出管理测试 ==========
    
    def test_set_and_get_node_output(self):
        """测试设置和获取节点输出（多端口）"""
        context = ExecutionContext(workflow_id="wf-123")
        outputs = {
            "output1": NodeOutput(data={"result": 42}),
            "output2": NodeOutput(data={"result": 100})
        }
        
        context.set_node_outputs("node1", outputs)
        
        # 获取所有输出
        retrieved = context.get_node_outputs("node1")
        assert retrieved is outputs
        
        # 获取单个端口输出
        output1 = context.get_node_output("node1", "output1")
        assert output1.data["result"] == 42
        
        output2 = context.get_node_output("node1", "output2")
        assert output2.data["result"] == 100
    
    def test_get_nonexistent_node_output(self):
        """测试获取不存在的节点输出"""
        context = ExecutionContext(workflow_id="wf-123")
        
        result = context.get_node_outputs("nonexistent")
        assert result is None
        
        result = context.get_node_output("nonexistent", "port1")
        assert result is None
    
    def test_has_node_output(self):
        """测试检查节点输出是否存在"""
        context = ExecutionContext(workflow_id="wf-123")
        outputs = {"output": NodeOutput()}
        
        assert not context.has_node_output("node1")
        assert not context.has_node_output("node1", "output")
        
        context.set_node_outputs("node1", outputs)
        assert context.has_node_output("node1")
        assert context.has_node_output("node1", "output")
        assert not context.has_node_output("node1", "nonexistent")
    
    def test_remove_node_output(self):
        """测试移除节点输出"""
        context = ExecutionContext(workflow_id="wf-123")
        outputs = {"output": NodeOutput()}
        
        context.set_node_outputs("node1", outputs)
        assert context.has_node_output("node1")
        
        context.remove_node_output("node1")
        assert not context.has_node_output("node1")
    
    def test_remove_nonexistent_node_output(self):
        """测试移除不存在的节点输出（不应报错）"""
        context = ExecutionContext(workflow_id="wf-123")
        context.remove_node_output("nonexistent")  # 不应报错
    
    def test_clear_node_outputs(self):
        """测试清空所有节点输出"""
        context = ExecutionContext(workflow_id="wf-123")
        
        context.set_node_outputs("node1", {"output": NodeOutput()})
        context.set_node_outputs("node2", {"output": NodeOutput()})
        assert len(context.node_outputs) == 2
        
        context.clear_node_outputs()
        assert len(context.node_outputs) == 0
    
    # ========== 节点输入管理测试 ==========
    
    def test_set_and_get_node_input(self):
        """测试设置和获取节点静态输入"""
        context = ExecutionContext(workflow_id="wf-123")
        
        context.set_node_input("step1_nl2sql", "question", "查询销售额")
        context.set_node_input("step1_nl2sql", "database", "sales_db")
        
        assert context.get_node_input("step1_nl2sql", "question") == "查询销售额"
        assert context.get_node_input("step1_nl2sql", "database") == "sales_db"
    
    def test_get_node_input_with_default(self):
        """测试获取节点输入（带默认值）"""
        context = ExecutionContext(workflow_id="wf-123")
        
        assert context.get_node_input("node1", "port1") is None
        assert context.get_node_input("node1", "port1", "default") == "default"
    
    def test_has_node_input(self):
        """测试检查节点输入是否存在"""
        context = ExecutionContext(workflow_id="wf-123")
        
        assert not context.has_node_input("node1", "port1")
        
        context.set_node_input("node1", "port1", "value")
        assert context.has_node_input("node1", "port1")
        assert not context.has_node_input("node1", "port2")
    
    def test_node_input_isolation(self):
        """测试节点输入的隔离性（不同节点、不同端口）"""
        context = ExecutionContext(workflow_id="wf-123")
        
        context.set_node_input("node1", "port1", "value1")
        context.set_node_input("node2", "port1", "value2")
        context.set_node_input("node1", "port2", "value3")
        
        assert context.get_node_input("node1", "port1") == "value1"
        assert context.get_node_input("node2", "port1") == "value2"
        assert context.get_node_input("node1", "port2") == "value3"
    
    # ========== 变量管理测试 ==========
    
    def test_set_and_get_variable(self):
        """测试设置和获取变量"""
        context = ExecutionContext(workflow_id="wf-123")
        
        context.set_variable("user_id", 42)
        context.set_variable("username", "alice")
        
        assert context.get_variable("user_id") == 42
        assert context.get_variable("username") == "alice"
    
    def test_get_variable_with_default(self):
        """测试获取变量（带默认值）"""
        context = ExecutionContext(workflow_id="wf-123")
        
        assert context.get_variable("nonexistent") is None
        assert context.get_variable("nonexistent", "default") == "default"
    
    def test_has_variable(self):
        """测试检查变量是否存在"""
        context = ExecutionContext(workflow_id="wf-123")
        
        assert not context.has_variable("key")
        
        context.set_variable("key", "value")
        assert context.has_variable("key")
    
    def test_remove_variable(self):
        """测试移除变量"""
        context = ExecutionContext(workflow_id="wf-123")
        
        context.set_variable("key", "value")
        assert context.has_variable("key")
        
        context.remove_variable("key")
        assert not context.has_variable("key")
    
    def test_clear_variables(self):
        """测试清空所有变量"""
        context = ExecutionContext(workflow_id="wf-123")
        
        context.set_variable("key1", "value1")
        context.set_variable("key2", "value2")
        assert len(context.variables) == 2
        
        context.clear_variables()
        assert len(context.variables) == 0
    
    # ========== 元数据管理测试 ==========
    
    def test_set_and_get_metadata(self):
        """测试设置和获取元数据"""
        context = ExecutionContext(workflow_id="wf-123")
        
        context.set_metadata("author", "alice")
        context.set_metadata("version", "1.0")
        
        assert context.get_metadata("author") == "alice"
        assert context.get_metadata("version") == "1.0"
    
    def test_get_metadata_with_default(self):
        """测试获取元数据（带默认值）"""
        context = ExecutionContext(workflow_id="wf-123")
        
        assert context.get_metadata("nonexistent") is None
        assert context.get_metadata("nonexistent", "default") == "default"
    
    # ========== 工具方法测试 ==========
    
    def test_clear(self):
        """测试清空所有数据"""
        context = ExecutionContext(workflow_id="wf-123")
        
        # 添加各种数据
        context.set_node_outputs("node1", {"output": NodeOutput()})
        context.set_variable("key", "value")
        context.set_metadata("author", "alice")
        
        workflow_id = context.workflow_id
        execution_id = context.execution_id
        created_at = context.created_at
        
        # 清空
        context.clear()
        
        # 数据已清空
        assert len(context.node_outputs) == 0
        assert len(context.variables) == 0
        assert len(context.metadata) == 0
        
        # IDs和创建时间保留
        assert context.workflow_id == workflow_id
        assert context.execution_id == execution_id
        assert context.created_at == created_at
    
    def test_clone(self):
        """测试克隆上下文"""
        context = ExecutionContext(workflow_id="wf-123")
        context.set_variable("key", "value")
        context.set_node_outputs("node1", {"output": NodeOutput()})
        context.set_metadata("author", "alice")
        
        # 克隆
        cloned = context.clone()
        
        # 不同的执行ID
        assert cloned.execution_id != context.execution_id
        
        # 相同的workflow_id
        assert cloned.workflow_id == context.workflow_id
        
        # 数据已复制
        assert cloned.get_variable("key") == "value"
        assert cloned.has_node_output("node1")
        assert cloned.get_metadata("author") == "alice"
        
        # 修改克隆不影响原对象
        cloned.set_variable("key", "new_value")
        assert context.get_variable("key") == "value"
    
    def test_to_dict(self):
        """测试转换为字典"""
        context = ExecutionContext(workflow_id="wf-123", execution_id="exec-456")
        context.set_variable("key", "value")
        outputs = {"output": NodeOutput(data={"result": 42})}
        context.set_node_outputs("node1", outputs)
        
        data = context.to_dict()
        
        assert data["workflow_id"] == "wf-123"
        assert data["execution_id"] == "exec-456"
        assert data["variables"]["key"] == "value"
        assert "node1" in data["node_outputs"]
        assert "output" in data["node_outputs"]["node1"]
        assert data["created_at"] is not None
    
    def test_repr(self):
        """测试字符串表示"""
        context = ExecutionContext(workflow_id="wf-123")
        context.set_node_outputs("node1", {"output": NodeOutput()})
        context.set_variable("key", "value")
        
        repr_str = repr(context)
        
        assert "ExecutionContext" in repr_str
        assert "wf-123" in repr_str
        assert "nodes=1" in repr_str
        assert "vars=1" in repr_str

