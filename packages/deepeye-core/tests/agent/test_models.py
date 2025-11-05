"""测试 Agent Models"""

import pytest

from deepeye.agent.models import (
    NodeConnection,
    ExecutionStep,
    ExecutionPlan,
    AgentResult,
    AgentStatus,
)


class TestNodeConnection:
    """测试 NodeConnection"""
    
    def test_create_connection(self):
        """测试创建节点连接"""
        conn = NodeConnection(
            from_step=1,
            from_port="data",
            to_port="database"
        )
        
        assert conn.from_step == 1
        assert conn.from_port == "data"
        assert conn.to_port == "database"


class TestExecutionStep:
    """测试 ExecutionStep"""
    
    def test_create_step(self):
        """测试创建步骤"""
        step = ExecutionStep(
            step_id=1,
            tool="DatabaseDataSource",
            description="连接数据库",
            static_inputs={
                "config": {  # 端口名
                    "connection_string": "sqlite:///sales.db"  # 参数名: 参数值
                }
            },
            config={},
            reasoning="需要先获取数据",
        )
        
        assert step.step_id == 1
        assert step.tool == "DatabaseDataSource"
        assert step.description == "连接数据库"
        assert len(step.static_inputs) == 1
        assert "config" in step.static_inputs
        assert step.static_inputs["config"]["connection_string"] == "sqlite:///sales.db"
        assert len(step.connections) == 0
        assert step.depends_on == []
    
    def test_step_with_dependencies(self):
        """测试带依赖的步骤"""
        step = ExecutionStep(
            step_id=2,
            tool="NL2SQL",
            description="生成SQL查询",
            connections=[
                NodeConnection(from_step=1, from_port="data", to_port="database")
            ],
            static_inputs={
                "query": {  # 端口名
                    "text": "查询销售额"  # 参数名: 参数值
                }
            },
            config={"model": "gpt-4"},
            reasoning="使用数据库信息生成SQL",
        )
        
        assert step.depends_on == [1]
        assert len(step.connections) == 1
        assert len(step.static_inputs) == 1
        assert "query" in step.static_inputs
        assert step.static_inputs["query"]["text"] == "查询销售额"
        assert step.connections[0].from_step == 1
        assert step.connections[0].from_port == "data"
        assert step.connections[0].to_port == "database"


class TestExecutionPlan:
    """测试 ExecutionPlan"""
    
    def test_create_plan(self):
        """测试创建计划"""
        plan = ExecutionPlan(
            task="查询并绘图",
            steps=[
                ExecutionStep(
                    step_id=1,
                    tool="NL2SQL",
                    description="查询数据",
                    static_inputs={},
                    config={},
                )
            ],
        )
        
        assert plan.task == "查询并绘图"
        assert len(plan.steps) == 1
    
    def test_get_step(self):
        """测试获取步骤"""
        step1 = ExecutionStep(
            step_id=1,
            tool="Tool1",
            description="Step 1",
            static_inputs={},
            config={},
        )
        step2 = ExecutionStep(
            step_id=2,
            tool="Tool2",
            description="Step 2",
            connections=[
                NodeConnection(from_step=1, from_port="output", to_port="data")
            ],
            config={},
        )
        
        plan = ExecutionPlan(task="test", steps=[step1, step2])
        
        assert plan.get_step(1) == step1
        assert plan.get_step(2) == step2
        assert plan.get_step(3) is None
    
    def test_validate_valid_plan(self):
        """测试验证有效计划"""
        plan = ExecutionPlan(
            task="test",
            steps=[
                ExecutionStep(
                    step_id=1,
                    tool="Tool1",
                    description="Step 1",
                    static_inputs={},
                    config={},
                ),
                ExecutionStep(
                    step_id=2,
                    tool="Tool2",
                    description="Step 2",
                    connections=[
                        NodeConnection(from_step=1, from_port="output", to_port="data")
                    ],
                    config={},
                ),
            ],
        )
        
        is_valid, errors = plan.validate()
        assert is_valid is True
        assert len(errors) == 0
    
    def test_validate_duplicate_step_id(self):
        """测试检测重复的步骤 ID"""
        plan = ExecutionPlan(
            task="test",
            steps=[
                ExecutionStep(
                    step_id=1,
                    tool="Tool1",
                    description="Step 1",
                    static_inputs={},
                    config={},
                ),
                ExecutionStep(
                    step_id=1,
                    tool="Tool2",
                    description="Step 1 duplicate",
                    static_inputs={},
                    config={},
                ),
            ],
        )
        
        is_valid, errors = plan.validate()
        assert is_valid is False
        assert any("重复的步骤 ID" in err for err in errors)
    
    def test_validate_invalid_dependency(self):
        """测试检测无效依赖"""
        plan = ExecutionPlan(
            task="test",
            steps=[
                ExecutionStep(
                    step_id=1,
                    tool="Tool1",
                    description="Step 1",
                    connections=[
                        NodeConnection(from_step=99, from_port="output", to_port="data")  # 不存在的步骤
                    ],
                    config={},
                ),
            ],
        )
        
        is_valid, errors = plan.validate()
        assert is_valid is False
        assert any("依赖不存在的步骤" in err for err in errors)
    
    def test_validate_self_dependency(self):
        """测试检测自依赖"""
        plan = ExecutionPlan(
            task="test",
            steps=[
                ExecutionStep(
                    step_id=1,
                    tool="Tool1",
                    description="Step 1",
                    connections=[
                        NodeConnection(from_step=1, from_port="output", to_port="data")  # 依赖自己
                    ],
                    config={},
                ),
            ],
        )
        
        is_valid, errors = plan.validate()
        assert is_valid is False
        assert any("不能依赖自己" in err for err in errors)
    
    def test_get_execution_order_linear(self):
        """测试获取线性执行顺序"""
        plan = ExecutionPlan(
            task="test",
            steps=[
                ExecutionStep(
                    step_id=1,
                    tool="Tool1",
                    description="Step 1",
                    static_inputs={},
                    config={},
                ),
                ExecutionStep(
                    step_id=2,
                    tool="Tool2",
                    description="Step 2",
                    connections=[
                        NodeConnection(from_step=1, from_port="output", to_port="data")
                    ],
                    config={},
                ),
                ExecutionStep(
                    step_id=3,
                    tool="Tool3",
                    description="Step 3",
                    connections=[
                        NodeConnection(from_step=2, from_port="output", to_port="data")
                    ],
                    config={},
                ),
            ],
        )
        
        order = plan.get_execution_order()
        assert order == [[1], [2], [3]]
    
    def test_get_execution_order_parallel(self):
        """测试获取并行执行顺序"""
        plan = ExecutionPlan(
            task="test",
            steps=[
                ExecutionStep(
                    step_id=1,
                    tool="Tool1",
                    description="Step 1",
                    static_inputs={},
                    config={},
                ),
                ExecutionStep(
                    step_id=2,
                    tool="Tool2",
                    description="Step 2",
                    static_inputs={},
                    config={},
                ),
                ExecutionStep(
                    step_id=3,
                    tool="Tool3",
                    description="Step 3",
                    connections=[
                        NodeConnection(from_step=1, from_port="output", to_port="data1"),
                        NodeConnection(from_step=2, from_port="output", to_port="data2"),
                    ],
                    config={},
                ),
            ],
        )
        
        order = plan.get_execution_order()
        assert len(order) == 2
        assert set(order[0]) == {1, 2}  # 步骤1和2可并行
        assert order[1] == [3]


class TestAgentResult:
    """测试 AgentResult"""
    
    def test_create_result(self):
        """测试创建结果"""
        result = AgentResult(task="test task")
        
        assert result.task == "test task"
        assert result.status == AgentStatus.PENDING
        assert result.success is False
    
    def test_add_log(self):
        """测试添加日志"""
        result = AgentResult(task="test")
        result.add_log("Log message 1")
        result.add_log("Log message 2")
        
        assert len(result.logs) == 2
        assert result.logs[0] == "Log message 1"
    
    def test_set_error(self):
        """测试设置错误"""
        result = AgentResult(task="test")
        result.set_error("Something went wrong")
        
        assert result.error == "Something went wrong"
        assert result.status == AgentStatus.FAILED
        assert result.success is False
        assert any("错误" in log for log in result.logs)
    
    def test_success_status(self):
        """测试成功状态"""
        result = AgentResult(task="test", status=AgentStatus.SUCCESS)
        
        assert result.success is True
    
    def test_to_dict(self):
        """测试转换为字典"""
        result = AgentResult(
            task="test task",
            status=AgentStatus.SUCCESS,
        )
        result.add_log("Log 1")
        result.plan = {"steps": []}
        
        dict_result = result.to_dict()
        
        assert dict_result["task"] == "test task"
        assert dict_result["status"] == "success"
        assert dict_result["success"] is True
        assert "plan" in dict_result
        assert "logs" in dict_result

