"""Planner Agent - 智能工作流规划器

基于 LLM 的任务规划器，将自然语言任务转换为可执行的工作流。
"""

import json
import re
from typing import Any, Dict, List, Optional, Type

from deepeye.llm.client import LLMClient, Message
from deepeye.nodes.base import BaseNode
from deepeye.workflow.engine import Workflow
from deepeye.runtime.context import ExecutionContext
from deepeye.agent.tool_layer import ToolRegistry
from deepeye.agent.models import (
    AgentResult,
    AgentStatus,
    ExecutionPlan,
    ExecutionStep,
)
from deepeye.agent.prompts import build_planner_prompt


class PlannerAgent:
    """Planner Agent - 基于 LLM 的工作流规划器
    
    核心流程：
    1. Planning: 分析任务，生成执行计划
    2. Building: 将执行计划转换为工作流
    3. Execution: 执行工作流（可选）
    4. Reflection: 评估结果（可选）
    
    Example:
        >>> from deepeye.llm import LLMClient
        >>> from deepeye.agent import PlannerAgent
        >>> from deepeye.nodes import NL2SQLNode
        
        >>> llm = LLMClient(api_key="sk-xxx")
        >>> agent = PlannerAgent(llm)
        >>> agent.register_node(NL2SQLNode)
        
        >>> result = agent.run("查询销售数据")
        >>> if result.success:
        ...     print(result.workflow.to_json())
    """
    
    def __init__(
        self,
        llm_client: LLMClient,
        model: str = "gpt-3.5-turbo",
        max_retries: int = 3,
        temperature: float = 0.3,
    ):
        """初始化 Planner Agent
        
        Args:
            llm_client: LLM 客户端
            model: 使用的模型名称
            max_retries: 最大重试次数
            temperature: LLM 温度参数（较低的值更确定性）
        """
        self.llm_client = llm_client
        self.model = model
        self.max_retries = max_retries
        self.temperature = temperature
        
        # 工具注册表
        self.tool_registry = ToolRegistry()
    
    def register_node(self, node_class: Type[BaseNode]) -> None:
        """注册节点类型为可用工具
        
        Args:
            node_class: 节点类
        """
        self.tool_registry.register_node(node_class)
    
    def run(
        self,
        task: str,
        auto_execute: bool = True,
    ) -> AgentResult:
        """运行 Agent 完成任务
        
        Args:
            task: 用户任务描述
            auto_execute: 是否自动执行工作流
            
        Returns:
            Agent 执行结果
        """
        result = AgentResult(task=task, status=AgentStatus.PENDING)
        
        try:
            # Phase 1: Planning
            result.add_log("=== Phase 1: Planning ===")
            result.status = AgentStatus.PLANNING
            
            plan = self._plan(task)
            result.plan = plan.model_dump()
            result.add_log(f"✓ Generated plan with {len(plan.steps)} steps")
            
            # 验证计划
            is_valid, errors = plan.validate()
            if not is_valid:
                error_msg = "执行计划验证失败:\n" + "\n".join(errors)
                result.set_error(error_msg)
                return result
            
            # Phase 2: Building Workflow
            result.add_log("\n=== Phase 2: Building Workflow ===")
            result.status = AgentStatus.BUILDING
            
            # 创建执行上下文（用于保存静态输入和配置）
            context = ExecutionContext(workflow_id="agent_generated")
            
            workflow = self._build_workflow(plan, context)
            result.workflow = workflow
            result.add_log(
                f"✓ Created workflow: {len(workflow.list_nodes())} nodes, "
                f"{len(workflow.get_connections())} connections"
            )
            
            # 验证工作流（传递 context 以支持静态输入验证）
            if not workflow.is_valid(context=context):
                report = workflow.get_validation_report(context=context)
                error_msg = "工作流验证失败:\n" + "\n".join(str(e) for e in report.errors)
                result.set_error(error_msg)
                return result
            
            result.add_log("✓ Workflow validation passed")
            
            # Phase 3: Execution (可选)
            if auto_execute:
                result.add_log("\n=== Phase 3: Execution ===")
                result.status = AgentStatus.EXECUTING
                
                exec_result = self._execute_workflow(workflow, context)
                result.execution_result = exec_result
                
                if exec_result.get("success", False):
                    result.add_log("✓ Workflow executed successfully")
                else:
                    # 提取错误信息
                    error_msg = exec_result.get("error")
                    if not error_msg and exec_result.get("errors"):
                        # 从 errors 字典中提取错误
                        errors_dict = exec_result.get("errors", {})
                        error_list = [f"{node_id}: {err}" for node_id, err in errors_dict.items()]
                        error_msg = "\n".join(error_list) if error_list else "Unknown error"
                    elif not error_msg:
                        error_msg = "Unknown error"
                    
                    result.set_error(f"工作流执行失败: {error_msg}")
                    return result
            
            # Success
            result.status = AgentStatus.SUCCESS
            result.add_log("\n=== Task Completed ===")
            result.add_log("✓ All phases completed successfully!")
            
        except Exception as e:
            result.set_error(f"Agent 执行失败: {type(e).__name__}: {str(e)}")
        
        return result
    
    def _plan(self, task: str) -> ExecutionPlan:
        """生成执行计划
        
        Args:
            task: 用户任务
            
        Returns:
            执行计划
            
        Raises:
            Exception: 规划失败
        """
        # 获取可用工具
        tools = self.tool_registry.list_tools()
        
        if not tools:
            raise ValueError("没有可用的工具，请先注册节点")
        
        # 构建 Prompt
        messages = build_planner_prompt(task, tools)
        llm_messages = [Message(**msg) for msg in messages]
        
        # 调用 LLM
        for attempt in range(self.max_retries):
            try:
                response = self.llm_client.generate(
                    messages=llm_messages,
                    model=self.model,
                    temperature=self.temperature,
                )
                
                # 解析响应
                plan_dict = self._parse_plan_response(response.content)
                
                print(f"plan_dict: {plan_dict}")
                
                # 构建 ExecutionPlan
                steps = []
                for step_data in plan_dict.get("steps", []):
                    step = ExecutionStep(**step_data)
                    steps.append(step)
                
                plan = ExecutionPlan(task=task, steps=steps)
                
                # 验证计划
                is_valid, errors = plan.validate()
                if is_valid:
                    return plan
                else:
                    # 计划无效，重试
                    if attempt < self.max_retries - 1:
                        # 添加错误信息到下一次尝试
                        error_msg = "上一次生成的计划无效:\n" + "\n".join(errors)
                        llm_messages.append(
                            Message(role="assistant", content=response.content)
                        )
                        llm_messages.append(
                            Message(role="user", content=f"{error_msg}\n请重新生成有效的计划。")
                        )
                        continue
                    else:
                        raise ValueError(f"生成的计划无效:\n" + "\n".join(errors))
            
            except json.JSONDecodeError as e:
                if attempt < self.max_retries - 1:
                    llm_messages.append(
                        Message(role="assistant", content=response.content)
                    )
                    llm_messages.append(
                        Message(role="user", content="响应格式错误，请输出有效的 JSON 格式")
                    )
                    continue
                else:
                    raise ValueError(f"无法解析 LLM 响应为 JSON: {e}")
        
        raise ValueError(f"经过 {self.max_retries} 次尝试仍未能生成有效的执行计划")
    
    def _parse_plan_response(self, content: str) -> Dict[str, Any]:
        """解析 LLM 响应为计划字典
        
        使用正则表达式提取 JSON 内容，支持以下格式：
        1. 纯 JSON
        2. Markdown 代码块中的 JSON: ```json ... ```
        3. 包含其他文本的响应（提取 JSON 部分）
        
        Args:
            content: LLM 响应文本
            
        Returns:
            计划字典
            
        Raises:
            ValueError: 无法提取有效的 JSON
        """
        content = content.strip()
        
        # 方法1: 尝试提取 markdown 代码块中的 JSON
        # 匹配 ```json ... ``` 或 ```JSON ... ``` 或 ``` ... ```
        code_block_pattern = r'```(?:json|JSON)?\s*\n?(.*?)\n?```'
        match = re.search(code_block_pattern, content, re.DOTALL | re.IGNORECASE)
        
        if match:
            json_content = match.group(1).strip()
            try:
                return json.loads(json_content)
            except json.JSONDecodeError:
                pass
        
        # 方法2: 尝试提取 JSON 对象（以 { 开始，以 } 结束）
        json_pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
        matches = re.finditer(json_pattern, content, re.DOTALL)
        
        for match in matches:
            json_str = match.group(0)
            try:
                plan_dict = json.loads(json_str)
                # 验证是否包含必需的字段
                if "steps" in plan_dict:
                    return plan_dict
            except json.JSONDecodeError:
                continue
        
        # 方法3: 尝试直接解析整个内容
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            pass
        
        raise ValueError(f"无法从响应中提取有效的 JSON 格式计划: {content[:200]}...")
    
    
    def _build_workflow(
        self,
        plan: ExecutionPlan,
        context: Optional[ExecutionContext] = None
    ) -> Workflow:
        """将执行计划转换为工作流
        
        Args:
            plan: 执行计划
            context: 执行上下文（可选）。如果提供，静态输入将设置到上下文中
            
        Returns:
            工作流对象
            
        注意：
            这个方法负责：
            1. 创建节点实例（不带 config）
            2. 根据 step.connections 建立节点连接
            3. 将静态输入（step.static_inputs）保存到执行上下文
        """
        workflow = Workflow(name="Agent Generated Workflow")
        
        # 创建节点映射：step_id -> node_id
        step_to_node = {}
        
        # 第一遍：创建所有节点
        for step in plan.steps:
            node_id = f"step{step.step_id}_{step.tool.lower()}"
            node = self.tool_registry.create_node_instance(
                tool_name=step.tool,
                node_id=node_id,
            )
            
            if node is None:
                raise ValueError(f"无法创建节点: {step.tool}")
            
            workflow.add_node(node_id, node)
            step_to_node[step.step_id] = node_id
        
        # 第二遍：建立连接和设置静态输入
        for step in plan.steps:
            current_node_id = step_to_node[step.step_id]
            
            # 处理节点连接（动态输入）
            for connection in step.connections:
                source_node_id = step_to_node[connection.from_step]
                
                # 建立连接
                workflow.connect(
                    from_node_id=source_node_id,
                    to_node_id=current_node_id,
                    from_port=connection.from_port,  # 前序节点的输出端口
                    to_port=connection.to_port,      # 当前节点的输入端口
                )
            
            # 处理静态输入
            if context is not None and step.static_inputs:
                for port_name, port_params in step.static_inputs.items():
                    # static_inputs 格式: {端口名: {参数名: 参数值, ...}}
                    # 需要将整个参数字典设置为端口输入
                    context.set_node_input(current_node_id, port_name, port_params)
        
        return workflow
    
    def _execute_workflow(
        self,
        workflow: Workflow,
        context: Optional[ExecutionContext] = None
    ) -> Dict[str, Any]:
        """执行工作流
        
        Args:
            workflow: 工作流对象
            context: 执行上下文（包含静态输入和配置）
            
        Returns:
            执行结果字典
        """
        from deepeye.runtime.workflow_executor import WorkflowExecutor
        
        try:
            executor = WorkflowExecutor(workflow, context=context)
            result = executor.execute()
            
            # 从 node_results 中提取输出和错误
            outputs = {}
            errors = {}
            for node_id, node_result in result.node_results.items():
                if node_result.outputs:
                    outputs[node_id] = {
                        port_name: output.model_dump() if hasattr(output, "model_dump") else str(output)
                        for port_name, output in node_result.outputs.items()
                    }
                if node_result.error:
                    errors[node_id] = str(node_result.error)
            
            return {
                "success": result.is_success(),
                "outputs": outputs,
                "errors": errors if errors else None,
            }
        
        except Exception as e:
            import traceback
            return {
                "success": False,
                "error": f"{type(e).__name__}: {str(e)}\n{traceback.format_exc()}",
            }

