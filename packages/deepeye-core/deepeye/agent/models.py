"""Agent 数据模型

定义 Agent 编排系统使用的核心数据结构。
"""

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from deepeye.workflow.engine import Workflow


class NodeConnection(BaseModel):
    """节点连接定义
    
    描述前序节点输出到当前节点输入的连接关系。
    """
    
    from_step: int = Field(description="来自哪个步骤（步骤 ID）")
    from_port: str = Field(description="前序节点的输出端口名称（如 'data', 'result'）")
    to_port: str = Field(description="当前节点的输入端口名称（如 'database', 'query'）")


class ExecutionStep(BaseModel):
    """执行步骤
    
    描述任务执行中的单个步骤。
    
    字段说明：
        - connections: 定义节点间的数据流连接（动态输入）
        - static_inputs: 定义静态输入参数（不依赖其他节点的输入）
        - config: 节点配置参数（用于初始化节点实例，如 model、temperature 等）
    
    Example:
        对于 NL2SQL 节点（有 database 和 query 两个输入端口）：
        ```python
        ExecutionStep(
            step_id=2,
            tool="NL2SQL",
            description="将自然语言转换为SQL并查询",
            connections=[
                # 连接：步骤1的data输出 -> 当前步骤的database输入
                NodeConnection(
                    from_step=1,
                    from_port="data",
                    to_port="database"
                )
            ],
            static_inputs={
                "query": {"text": "查询2024年销售额前10的产品"}
            }
        )
        ```
    """
    
    step_id: int = Field(description="步骤 ID（唯一）")
    tool: str = Field(description="使用的工具名称（节点类型）")
    description: str = Field(description="步骤描述")
    connections: List[NodeConnection] = Field(
        default_factory=list,
        description="节点连接列表（定义来自前序节点的动态输入）"
    )
    static_inputs: Dict[str, Dict[str, Any]] = Field(
        default_factory=dict,
        description="静态输入：外层key为端口名，内层key为参数名，value为参数值"
    )
    
    @property
    def depends_on(self) -> List[int]:
        """获取依赖的步骤 ID 列表（从 connections 中自动提取）"""
        deps = [conn.from_step for conn in self.connections]
        return sorted(set(deps))  # 去重并排序


class ExecutionPlan(BaseModel):
    """执行计划
    
    包含完整的任务执行步骤列表。
    """
    
    task: str = Field(description="原始任务描述")
    steps: List[ExecutionStep] = Field(
        default_factory=list,
        description="执行步骤列表"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="额外元数据"
    )
    
    def get_step(self, step_id: int) -> Optional[ExecutionStep]:
        """获取指定 ID 的步骤
        
        Args:
            step_id: 步骤 ID
            
        Returns:
            步骤对象，如果不存在则返回 None
        """
        for step in self.steps:
            if step.step_id == step_id:
                return step
        return None
    
    def validate(self) -> tuple[bool, List[str]]:
        """验证执行计划
        
        Returns:
            (是否有效, 错误消息列表)
        """
        errors = []
        step_ids = set()
        
        # 检查步骤 ID 唯一性
        for step in self.steps:
            if step.step_id in step_ids:
                errors.append(f"重复的步骤 ID: {step.step_id}")
            step_ids.add(step.step_id)
        
        # 检查依赖关系有效性
        for step in self.steps:
            for dep_id in step.depends_on:
                if dep_id not in step_ids:
                    errors.append(
                        f"步骤 {step.step_id} 依赖不存在的步骤: {dep_id}"
                    )
                elif dep_id >= step.step_id:
                    errors.append(
                        f"步骤 {step.step_id} 不能依赖后续步骤: {dep_id}"
                    )
        
        # 检查是否有循环依赖（简单检查）
        for step in self.steps:
            if step.step_id in step.depends_on:
                errors.append(f"步骤 {step.step_id} 不能依赖自己")
        
        return len(errors) == 0, errors
    
    def get_execution_order(self) -> List[List[int]]:
        """获取执行顺序（按层级分组）
        
        Returns:
            执行顺序，每个子列表包含可以并行执行的步骤 ID
        """
        # 构建依赖图
        remaining = {step.step_id: set(step.depends_on) for step in self.steps}
        result = []
        
        while remaining:
            # 找出没有依赖的步骤（当前层）
            current_layer = [
                step_id for step_id, deps in remaining.items()
                if not deps
            ]
            
            if not current_layer:
                # 存在循环依赖
                break
            
            result.append(current_layer)
            
            # 移除已执行的步骤
            for step_id in current_layer:
                del remaining[step_id]
            
            # 更新其他步骤的依赖
            for deps in remaining.values():
                deps.difference_update(current_layer)
        
        return result


class AgentStatus(str, Enum):
    """Agent 执行状态"""
    
    PENDING = "pending"
    PLANNING = "planning"
    BUILDING = "building"
    EXECUTING = "executing"
    REFLECTING = "reflecting"
    SUCCESS = "success"
    FAILED = "failed"


class AgentResult(BaseModel):
    """Agent 执行结果
    
    包含执行计划、工作流、执行结果等完整信息。
    """
    
    task: str = Field(description="原始任务描述")
    status: AgentStatus = Field(
        default=AgentStatus.PENDING,
        description="执行状态"
    )
    plan: Optional[Dict[str, Any]] = Field(
        default=None,
        description="执行计划（字典格式）"
    )
    workflow: Optional[Workflow] = Field(
        default=None,
        description="生成的工作流"
    )
    execution_result: Optional[Dict[str, Any]] = Field(
        default=None,
        description="工作流执行结果"
    )
    error: Optional[str] = Field(
        default=None,
        description="错误信息"
    )
    logs: List[str] = Field(
        default_factory=list,
        description="执行日志"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="额外元数据"
    )
    
    model_config = {
        "arbitrary_types_allowed": True
    }
    
    @property
    def success(self) -> bool:
        """是否执行成功"""
        return self.status == AgentStatus.SUCCESS
    
    def add_log(self, message: str) -> None:
        """添加日志
        
        Args:
            message: 日志消息
        """
        self.logs.append(message)
    
    def set_error(self, error: str) -> None:
        """设置错误
        
        Args:
            error: 错误消息
        """
        self.error = error
        self.status = AgentStatus.FAILED
        self.add_log(f"❌ 错误: {error}")
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        result = {
            "task": self.task,
            "status": self.status.value,
            "success": self.success,
            "logs": self.logs,
            "metadata": self.metadata,
        }
        
        if self.plan:
            result["plan"] = self.plan
        
        if self.workflow:
            result["workflow"] = {
                "name": self.workflow.name,
                "nodes": self.workflow.list_nodes(),
                "connections": [
                    {"from": conn[0], "to": conn[1]}
                    for conn in self.workflow.get_connections()
                ],
            }
        
        if self.execution_result:
            result["execution_result"] = self.execution_result
        
        if self.error:
            result["error"] = self.error
        
        return result

