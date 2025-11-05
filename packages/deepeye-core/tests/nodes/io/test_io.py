"""测试节点输入输出"""

import pytest
from deepeye.nodes.io import (
    NodeInput,
    NodeInputSchema,
    NodeInputPort,
    NodeOutput,
    NodeOutputSchema,
    NodeOutputPort,
    NodeStatus,
)


def test_node_input_creation():
    """测试创建节点输入"""
    input_data = NodeInput(
        data={"key": "value"},
        metadata={"source": "test"},
        context={"user_id": "123"}
    )
    
    assert input_data.data == {"key": "value"}
    assert input_data.metadata == {"source": "test"}
    assert input_data.context == {"user_id": "123"}


def test_node_input_get():
    """测试获取输入数据"""
    input_data = NodeInput(data={"name": "Alice", "age": 25})
    
    assert input_data.get("name") == "Alice"
    assert input_data.get("age") == 25
    assert input_data.get("nonexistent", "default") == "default"


def test_node_input_update():
    """测试更新输入数据"""
    input_data = NodeInput(data={"name": "Alice"})
    input_data.update(age=25, city="Beijing")
    
    assert input_data.data["name"] == "Alice"
    assert input_data.data["age"] == 25
    assert input_data.data["city"] == "Beijing"


def test_node_input_has():
    """测试检查输入数据是否包含键"""
    input_data = NodeInput(data={"name": "Alice"})
    
    assert input_data.has("name")
    assert not input_data.has("age")


def test_node_output_creation():
    """测试创建节点输出"""
    output = NodeOutput(
        data={"result": [1, 2, 3]},
        status=NodeStatus.SUCCESS,
        metadata={"count": 3}
    )
    
    assert output.data == {"result": [1, 2, 3]}
    assert output.status == NodeStatus.SUCCESS
    assert output.metadata == {"count": 3}


def test_node_output_status():
    """测试节点输出状态"""
    output = NodeOutput(status=NodeStatus.SUCCESS)
    assert output.is_success()
    assert not output.is_failed()
    
    output.status = NodeStatus.FAILED
    assert not output.is_success()
    assert output.is_failed()


def test_node_output_logs():
    """测试节点输出日志"""
    output = NodeOutput()
    
    output.add_log("Step 1")
    output.add_log("Step 2")
    
    assert len(output.logs) == 2
    assert output.logs[0] == "Step 1"
    assert output.logs[1] == "Step 2"


def test_node_output_error():
    """测试设置错误"""
    output = NodeOutput()
    
    output.set_error("Something went wrong")
    
    assert output.error == "Something went wrong"
    assert output.status == NodeStatus.FAILED
    assert output.is_failed()


def test_node_output_metrics():
    """测试节点输出指标"""
    output = NodeOutput()
    
    output.set_metric("duration_ms", 1250)
    output.set_metric("tokens_used", 450)
    
    assert output.get_metric("duration_ms") == 1250
    assert output.get_metric("tokens_used") == 450
    assert output.get_metric("nonexistent", 0) == 0


def test_node_input_schema():
    """测试节点输入模式"""
    schema = NodeInputSchema(
        name="query",
        type="string",
        required=True,
        description="SQL查询语句"
    )
    
    assert schema.name == "query"
    assert schema.type == "string"
    assert schema.required
    assert schema.description == "SQL查询语句"


def test_node_input_schema_validation():
    """测试输入模式验证"""
    schema = NodeInputSchema(name="age", type="integer", required=True)
    
    assert schema.validate_value(25)
    assert not schema.validate_value("25")
    assert not schema.validate_value(None)


def test_node_input_schema_optional():
    """测试可选输入模式"""
    schema = NodeInputSchema(name="optional", type="string", required=False)
    
    assert schema.validate_value("value")
    assert schema.validate_value(None)  # 可选参数允许 None


def test_node_input_port():
    """测试节点输入端口"""
    port = NodeInputPort(
        name="data",
        label="数据输入",
        schemas=[
            NodeInputSchema(name="query", type="string", required=True)
        ]
    )
    
    assert port.name == "data"
    assert port.label == "数据输入"
    assert len(port.schemas) == 1


def test_node_input_port_validation():
    """测试输入端口验证"""
    port = NodeInputPort(
        name="data",
        schemas=[
            NodeInputSchema(name="query", type="string", required=True),
            NodeInputSchema(name="limit", type="integer", required=False)
        ]
    )
    
    # 有效输入
    valid_input = NodeInput(data={"query": "SELECT * FROM users", "limit": 10})
    is_valid, errors = port.validate_input(valid_input)
    assert is_valid
    assert len(errors) == 0
    
    # 缺少必需参数
    invalid_input = NodeInput(data={"limit": 10})
    is_valid, errors = port.validate_input(invalid_input)
    assert not is_valid
    assert len(errors) > 0


def test_node_output_schema():
    """测试节点输出模式"""
    schema = NodeOutputSchema(
        name="result",
        type="array",
        description="查询结果集"
    )
    
    assert schema.name == "result"
    assert schema.type == "array"
    assert schema.description == "查询结果集"


def test_node_output_port():
    """测试节点输出端口"""
    port = NodeOutputPort(
        name="result",
        label="查询结果",
        schemas=[
            NodeOutputSchema(name="data", type="array", description="数据")
        ]
    )
    
    assert port.name == "result"
    assert port.label == "查询结果"
    assert len(port.schemas) == 1


def test_node_status_enum():
    """测试节点状态枚举"""
    assert NodeStatus.PENDING == "pending"
    assert NodeStatus.RUNNING == "running"
    assert NodeStatus.SUCCESS == "success"
    assert NodeStatus.FAILED == "failed"
    assert NodeStatus.SKIPPED == "skipped"
    assert NodeStatus.CANCELLED == "cancelled"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])


