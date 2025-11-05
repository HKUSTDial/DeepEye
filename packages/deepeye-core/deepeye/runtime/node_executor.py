"""节点执行器

负责单个节点的执行逻辑，包括输入准备、节点执行和结果保存。
"""

from typing import Dict, Optional, TYPE_CHECKING
import traceback

from deepeye.nodes import NodeInput
from deepeye.runtime.context import ExecutionContext
from deepeye.runtime.result import NodeExecutionResult, ExecutionStatus
from deepeye.exceptions import NodeExecutionError

if TYPE_CHECKING:
    from deepeye.nodes import BaseNode
    from deepeye.workflow import Workflow


class NodeExecutor:
    """节点执行器
    
    负责执行单个节点，包括：
    1. 从执行上下文中准备输入数据
    2. 执行节点逻辑
    3. 将输出保存到执行上下文
    4. 错误处理
    
    Attributes:
        context: 执行上下文，用于存储和获取节点输出
    
    Examples:
        >>> from deepeye.runtime import ExecutionContext, NodeExecutor
        >>> from deepeye.workflow import Workflow
        >>> 
        >>> # 创建执行上下文和执行器
        >>> context = ExecutionContext(workflow_id="wf1", execution_id="exec1")
        >>> executor = NodeExecutor(context)
        >>> 
        >>> # 执行节点
        >>> result = executor.execute_node("node1", node, workflow)
        >>> print(result.status)  # SUCCESS or FAILED
    """
    
    def __init__(self, context: ExecutionContext):
        """初始化节点执行器
        
        Args:
            context: 执行上下文
        """
        self.context = context
    
    def prepare_inputs(
        self,
        node_id: str,
        node: "BaseNode",
        workflow: "Workflow"
    ) -> Dict[str, NodeInput]:
        """准备节点的输入数据
        
        根据工作流的连接定义，从执行上下文中获取前驱节点的输出，
        并映射到当前节点的输入端口。同时也会从 context 中获取静态输入。
        
        Args:
            node_id: 节点ID
            node: 节点实例
            workflow: 工作流实例
        
        Returns:
            输入端口名称到 NodeInput 的映射
        
        Raises:
            NodeExecutionError: 当必需的输入缺失或映射错误时
        
        Examples:
            >>> inputs = executor.prepare_inputs("node2", node2, workflow)
            >>> # inputs = {"data": NodeInput(...), "config": NodeInput(...)}
        """
        inputs: Dict[str, NodeInput] = {}
        
        # 获取所有指向该节点的连接
        incoming_connections = [
            conn for conn in workflow.graph.get_connections()
            if conn.to_node_id == node_id
        ]
        
        # 为每个连接准备输入（动态输入）
        for conn in incoming_connections:
            # 从上下文获取源节点的输出
            source_outputs = self.context.get_node_outputs(conn.from_node_id)
            
            if source_outputs is None:
                raise NodeExecutionError(
                    f"节点 '{node_id}' 的前驱节点 '{conn.from_node_id}' 尚未执行或没有输出"
                )
            
            # 获取指定端口的输出
            if conn.from_port not in source_outputs:
                available_ports = list(source_outputs.keys())
                raise NodeExecutionError(
                    f"节点 '{conn.from_node_id}' 没有输出端口 '{conn.from_port}'，"
                    f"可用端口: {available_ports}"
                )
            
            source_output = source_outputs[conn.from_port]
            
            # 将输出数据转换为 NodeInput
            # NodeOutput.data -> NodeInput.data
            node_input = NodeInput(
                data=source_output.data,
                metadata={
                    **source_output.metadata,
                    "from_node": conn.from_node_id,
                    "from_port": conn.from_port,
                }
            )
            
            # 映射到目标节点的输入端口
            if conn.to_port in inputs:
                # 同一个输入端口不应该有多个连接
                # 这应该在工作流验证时就被发现
                raise NodeExecutionError(
                    f"节点 '{node_id}' 的输入端口 '{conn.to_port}' "
                    f"有多个连接，这是不允许的"
                )
            
            inputs[conn.to_port] = node_input
        
        # 从 context 中获取静态输入（用于 Agent 模式）
        for port in node.input_ports:
            # 如果端口已经有连接提供的输入，跳过
            if port.name in inputs:
                continue
            
            # 尝试从 context 中获取静态输入
            static_input = self.context.get_node_input(node_id, port.name)
            if static_input is not None:
                inputs[port.name] = NodeInput(
                    data=static_input,
                    metadata={"source": "static_input"}
                )
        
        return inputs
    
    def execute_node(
        self,
        node_id: str,
        node: "BaseNode",
        workflow: "Workflow"
    ) -> NodeExecutionResult:
        """执行单个节点
        
        完整的节点执行流程：
        1. 创建执行结果对象
        2. 准备输入数据
        3. 执行节点逻辑
        4. 保存输出到上下文
        5. 记录结果
        
        Args:
            node_id: 节点ID
            node: 节点实例
            workflow: 工作流实例
        
        Returns:
            节点执行结果
        
        Examples:
            >>> result = executor.execute_node("node1", node1, workflow)
            >>> if result.status == ExecutionStatus.SUCCESS:
            ...     print("节点执行成功")
            ... else:
            ...     print(f"节点执行失败: {result.error}")
        """
        # 创建执行结果对象
        result = NodeExecutionResult(node_id=node_id)
        result.mark_started()
        
        try:
            # 1. 准备输入
            inputs = self.prepare_inputs(node_id, node, workflow)
            
            # 2. 执行节点
            outputs = node.run(inputs)
            
            # 检查是否有错误的输出
            has_error = any(
                output.is_failed() for output in outputs.values()
            )
            
            if has_error:
                # 提取错误信息
                error_output = next(
                    output for output in outputs.values() if output.is_failed()
                )
                error_msg = error_output.error or "节点执行失败"
                result.mark_failed(Exception(error_msg))
            else:
                # 3. 保存输出到上下文
                self.context.set_node_outputs(node_id, outputs)
                
                # 4. 标记成功
                result.mark_success(outputs)
            
        except Exception as e:
            # 错误处理
            result.mark_failed(e)
        
        return result
    
    def execute_with_provided_inputs(
        self,
        node_id: str,
        node: "BaseNode",
        inputs: Dict[str, NodeInput]
    ) -> NodeExecutionResult:
        """使用提供的输入执行节点
        
        不从工作流上下文中准备输入，而是直接使用提供的输入。
        通常用于执行根节点（没有前驱节点的节点）。
        
        Args:
            node_id: 节点ID
            node: 节点实例
            inputs: 提供的输入数据
        
        Returns:
            节点执行结果
        
        Examples:
            >>> # 为根节点提供外部输入
            >>> inputs = {"data": NodeInput(data={"value": 42})}
            >>> result = executor.execute_with_provided_inputs(
            ...     "source_node", source_node, inputs
            ... )
        """
        result = NodeExecutionResult(node_id=node_id)
        result.mark_started()
        
        try:
            # 执行节点
            outputs = node.run(inputs)
            
            # 检查是否有错误的输出
            has_error = any(
                output.is_failed() for output in outputs.values()
            )
            
            if has_error:
                # 提取错误信息
                error_output = next(
                    output for output in outputs.values() if output.is_failed()
                )
                error_msg = error_output.error or "节点执行失败"
                result.mark_failed(Exception(error_msg))
            else:
                # 保存输出到上下文
                self.context.set_node_outputs(node_id, outputs)
                
                # 标记成功
                result.mark_success(outputs)
            
        except Exception as e:
            # 错误处理（如果 node.run 抛出异常）
            result.mark_failed(e)
        
        return result

