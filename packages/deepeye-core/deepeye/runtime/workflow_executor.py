"""工作流执行器

负责完整工作流的执行，包括拓扑排序、顺序执行和结果收集。
"""

from typing import Dict, Optional, Any, List
from datetime import datetime
import uuid

from deepeye.workflow import Workflow
from deepeye.nodes import NodeInput
from deepeye.runtime.context import ExecutionContext
from deepeye.runtime.node_executor import NodeExecutor
from deepeye.runtime.result import WorkflowExecutionResult, ExecutionStatus
from deepeye.exceptions import WorkflowExecutionError


class WorkflowExecutor:
    """工作流执行器
    
    负责执行完整的工作流，包括：
    1. 工作流验证
    2. 按拓扑顺序执行节点
    3. 处理节点间的数据流
    4. 收集执行结果
    5. 错误处理和传播
    
    Attributes:
        workflow: 工作流实例
        context: 执行上下文
        node_executor: 节点执行器
        fail_fast: 是否快速失败（一个节点失败后立即停止）
    
    Examples:
        >>> from deepeye.workflow import Workflow
        >>> from deepeye.runtime import WorkflowExecutor
        >>> 
        >>> # 创建工作流
        >>> workflow = Workflow(name="my_workflow")
        >>> # ... 添加节点和连接 ...
        >>> 
        >>> # 执行工作流
        >>> executor = WorkflowExecutor(workflow)
        >>> result = executor.execute()
        >>> 
        >>> if result.is_success():
        ...     print("工作流执行成功")
    """
    
    def __init__(
        self,
        workflow: Workflow,
        execution_id: Optional[str] = None,
        context: Optional[ExecutionContext] = None,
        fail_fast: bool = True
    ):
        """初始化工作流执行器
        
        Args:
            workflow: 工作流实例
            execution_id: 执行 ID（可选，默认自动生成）
            context: 执行上下文（可选）。如果提供，将使用该上下文而不是创建新的
            fail_fast: 是否快速失败（默认 True）
        """
        self.workflow = workflow
        self.fail_fast = fail_fast
        
        # 使用提供的上下文或创建新的
        if context is not None:
            self.context = context
            # 如果上下文没有正确的workflow_id，更新它
            if self.context.workflow_id != workflow.workflow_id:
                self.context.workflow_id = workflow.workflow_id
        else:
            # 创建新的执行上下文
            exec_id = execution_id or f"exec-{uuid.uuid4().hex[:8]}"
            self.context = ExecutionContext(
                workflow_id=workflow.workflow_id,
                execution_id=exec_id
            )
        
        # 创建节点执行器
        self.node_executor = NodeExecutor(self.context)
    
    def execute(
        self,
        inputs: Optional[Dict[str, Dict[str, Any]]] = None
    ) -> WorkflowExecutionResult:
        """执行工作流
        
        按拓扑顺序执行所有节点，处理节点间的数据流。
        
        Args:
            inputs: 根节点的外部输入，格式为:
                {
                    "node_id": {
                        "port_name": {"key": "value"}
                    }
                }
                例如: {"source_node": {"data": {"value": 42}}}
        
        Returns:
            工作流执行结果
        
        Raises:
            WorkflowExecutionError: 如果工作流验证失败或执行过程中发生错误
        
        Examples:
            >>> # 无输入执行
            >>> result = executor.execute()
            >>> 
            >>> # 为根节点提供输入
            >>> inputs = {
            ...     "source": {"data": {"value": 100}}
            ... }
            >>> result = executor.execute(inputs=inputs)
        """
        # 创建执行结果
        result = WorkflowExecutionResult(
            workflow_id=self.workflow.workflow_id,
            execution_id=self.context.execution_id
        )
        
        result.mark_started()
        
        try:
            # 1. 验证工作流
            self._validate_workflow()
            
            # 2. 准备根节点输入
            root_inputs = self._prepare_root_inputs(inputs or {})
            
            # 3. 获取执行顺序
            execution_order = self._get_execution_order()
            
            # 4. 按顺序执行节点
            for node_id in execution_order:
                # 检查是否应该继续执行
                if self.fail_fast and result.has_failed_nodes():
                    # 标记剩余节点为跳过
                    remaining_nodes = execution_order[execution_order.index(node_id):]
                    for remaining_id in remaining_nodes:
                        from deepeye.runtime.result import NodeExecutionResult
                        skipped_result = NodeExecutionResult(node_id=remaining_id)
                        skipped_result.mark_skipped()
                        result.add_node_result(skipped_result)
                    break
                
                # 执行节点
                node_result = self._execute_node(node_id, root_inputs)
                result.add_node_result(node_result)
            
            # 5. 设置最终状态
            if result.has_failed_nodes():
                result.mark_failed()
            else:
                result.mark_success()
        
        except Exception as e:
            # 处理执行过程中的异常
            result.mark_failed()
            # 可以在这里添加更详细的错误信息
            raise WorkflowExecutionError(
                f"工作流执行失败: {type(e).__name__}: {str(e)}"
            ) from e
        
        return result
    
    def _validate_workflow(self) -> None:
        """验证工作流
        
        检查工作流是否有效，包括：
        - 图结构是否为 DAG
        - 节点是否都有实例
        - 连接是否有效
        - 必需输入是否都有连接或静态输入
        
        Raises:
            WorkflowExecutionError: 如果验证失败
        """
        try:
            # 使用 raise_on_error=True 和 context 来让验证失败时抛出异常
            # 传递 context 以支持静态输入的验证
            self.workflow.validate(raise_on_error=True, context=self.context)
        except Exception as e:
            raise WorkflowExecutionError(
                f"工作流验证失败: {str(e)}"
            ) from e
    
    def _prepare_root_inputs(
        self,
        inputs: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Dict[str, NodeInput]]:
        """准备根节点的输入
        
        将用户提供的输入数据转换为 NodeInput 对象。
        
        Args:
            inputs: 用户提供的输入数据
        
        Returns:
            转换后的输入，格式为 {node_id: {port_name: NodeInput}}
        """
        root_inputs: Dict[str, Dict[str, NodeInput]] = {}
        
        for node_id, port_data in inputs.items():
            root_inputs[node_id] = {}
            for port_name, data in port_data.items():
                root_inputs[node_id][port_name] = NodeInput(data=data)
        
        return root_inputs
    
    def _get_execution_order(self) -> List[str]:
        """获取节点执行顺序
        
        使用拓扑排序确定节点的执行顺序，确保每个节点在其
        所有依赖节点之后执行。
        
        Returns:
            节点 ID 列表，按执行顺序排列
        
        Raises:
            WorkflowExecutionError: 如果无法确定执行顺序（如有循环依赖）
        """
        try:
            return self.workflow.graph.get_topological_order()
        except Exception as e:
            raise WorkflowExecutionError(
                f"无法确定节点执行顺序: {str(e)}"
            ) from e
    
    def _execute_node(
        self,
        node_id: str,
        root_inputs: Dict[str, Dict[str, NodeInput]]
    ):
        """执行单个节点
        
        根据节点是否为根节点，选择不同的执行方式。
        
        Args:
            node_id: 节点 ID
            root_inputs: 根节点的外部输入
        
        Returns:
            节点执行结果
        """
        node = self.workflow.nodes[node_id]
        
        # 检查是否为根节点（没有前驱节点）
        predecessors = self.workflow.graph.get_predecessors(node_id)
        
        if len(predecessors) == 0 and node_id in root_inputs:
            # 根节点，使用提供的输入
            return self.node_executor.execute_with_provided_inputs(
                node_id,
                node,
                root_inputs[node_id]
            )
        else:
            # 非根节点，从上下文中准备输入
            return self.node_executor.execute_node(
                node_id,
                node,
                self.workflow
            )
    
    def get_execution_layers(self) -> List[List[str]]:
        """获取可并行执行的层级
        
        将节点按深度分组，同一层级的节点可以并行执行。
        
        Returns:
            节点层级列表，每层是一个节点 ID 列表
        
        Examples:
            >>> layers = executor.get_execution_layers()
            >>> # [[root_nodes], [layer1_nodes], [layer2_nodes], ...]
        """
        return self.workflow.graph.get_execution_layers()
    
    def execute_parallel(
        self,
        inputs: Optional[Dict[str, Dict[str, Any]]] = None
    ) -> WorkflowExecutionResult:
        """并行执行工作流（未来功能）
        
        按层级并行执行节点，同一层级的节点可以同时执行。
        
        Args:
            inputs: 根节点的外部输入
        
        Returns:
            工作流执行结果
        
        Note:
            这是一个占位方法，实际的并行执行将在 Phase 4 中实现。
        """
        raise NotImplementedError(
            "并行执行功能将在 Phase 4 中实现。"
            "目前请使用 execute() 方法进行顺序执行。"
        )

