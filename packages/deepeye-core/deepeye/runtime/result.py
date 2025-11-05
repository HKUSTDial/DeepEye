"""执行结果模块

定义节点和工作流的执行结果。
"""

from enum import Enum
from typing import Dict, List, Optional, Any
from datetime import datetime
from deepeye.nodes.io import NodeOutput


class ExecutionStatus(str, Enum):
    """执行状态枚举"""
    
    PENDING = "pending"      # 等待执行
    RUNNING = "running"      # 执行中
    SUCCESS = "success"      # 执行成功
    FAILED = "failed"        # 执行失败
    SKIPPED = "skipped"      # 跳过执行
    CANCELLED = "cancelled"  # 已取消
    
    def is_terminal(self) -> bool:
        """是否为终止状态
        
        Returns:
            是否为终止状态（SUCCESS, FAILED, SKIPPED, CANCELLED）
        """
        return self in (
            ExecutionStatus.SUCCESS,
            ExecutionStatus.FAILED,
            ExecutionStatus.SKIPPED,
            ExecutionStatus.CANCELLED
        )
    
    def is_successful(self) -> bool:
        """是否为成功状态
        
        Returns:
            是否为成功状态
        """
        return self == ExecutionStatus.SUCCESS


class NodeExecutionResult:
    """节点执行结果
    
    记录单个节点的执行情况。
    
    Attributes:
        node_id: 节点ID
        status: 执行状态
        outputs: 节点输出（端口名称到输出对象的映射）
        error: 错误信息（如果失败）
        start_time: 开始时间
        end_time: 结束时间
        duration: 执行耗时（秒）
        metadata: 额外的元数据
    """
    
    def __init__(
        self,
        node_id: str,
        status: ExecutionStatus = ExecutionStatus.PENDING,
        outputs: Optional[Dict[str, NodeOutput]] = None,
        error: Optional[Exception] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """初始化节点执行结果
        
        Args:
            node_id: 节点ID
            status: 执行状态
            outputs: 节点输出（端口名称到输出对象的映射）
            error: 错误信息
            start_time: 开始时间
            end_time: 结束时间
            metadata: 元数据
        """
        self.node_id = node_id
        self.status = status
        self.outputs = outputs
        self.error = error
        self.start_time = start_time or datetime.now()
        self.end_time = end_time
        self.metadata = metadata or {}
    
    @property
    def duration(self) -> Optional[float]:
        """计算执行耗时（秒）
        
        Returns:
            耗时（秒），如果未结束返回None
        """
        if self.end_time is None:
            return None
        return (self.end_time - self.start_time).total_seconds()
    
    def mark_started(self) -> None:
        """标记为开始执行"""
        self.status = ExecutionStatus.RUNNING
        self.start_time = datetime.now()
    
    def mark_success(self, outputs: Dict[str, NodeOutput]) -> None:
        """标记为执行成功
        
        Args:
            outputs: 节点输出（端口名称到输出对象的映射）
        """
        self.status = ExecutionStatus.SUCCESS
        self.outputs = outputs
        self.end_time = datetime.now()
    
    def mark_failed(self, error: Exception) -> None:
        """标记为执行失败
        
        Args:
            error: 错误信息
        """
        self.status = ExecutionStatus.FAILED
        self.error = error
        self.end_time = datetime.now()
    
    def mark_skipped(self) -> None:
        """标记为跳过执行"""
        self.status = ExecutionStatus.SKIPPED
        self.end_time = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典
        
        Returns:
            字典表示
        """
        result = {
            "node_id": self.node_id,
            "status": self.status.value,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration": self.duration,
            "metadata": self.metadata,
        }
        
        if self.outputs:
            result["outputs"] = {
                port_name: output.model_dump()
                for port_name, output in self.outputs.items()
            }
        
        if self.error:
            result["error"] = {
                "type": type(self.error).__name__,
                "message": str(self.error)
            }
        
        return result
    
    def __repr__(self) -> str:
        """字符串表示"""
        return (
            f"NodeExecutionResult("
            f"node_id='{self.node_id}', "
            f"status={self.status.value}, "
            f"duration={self.duration:.2f}s)" if self.duration else f"duration=None)"
        )


class WorkflowExecutionResult:
    """工作流执行结果
    
    记录整个工作流的执行情况。
    
    Attributes:
        workflow_id: 工作流ID
        execution_id: 执行ID
        status: 整体执行状态
        node_results: 节点执行结果字典
        start_time: 开始时间
        end_time: 结束时间
        duration: 执行耗时（秒）
        metadata: 额外的元数据
    """
    
    def __init__(
        self,
        workflow_id: str,
        execution_id: str,
        status: ExecutionStatus = ExecutionStatus.PENDING,
        node_results: Optional[Dict[str, NodeExecutionResult]] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """初始化工作流执行结果
        
        Args:
            workflow_id: 工作流ID
            execution_id: 执行ID
            status: 执行状态
            node_results: 节点执行结果
            start_time: 开始时间
            end_time: 结束时间
            metadata: 元数据
        """
        self.workflow_id = workflow_id
        self.execution_id = execution_id
        self.status = status
        self.node_results: Dict[str, NodeExecutionResult] = node_results or {}
        self.start_time = start_time or datetime.now()
        self.end_time = end_time
        self.metadata = metadata or {}
    
    @property
    def duration(self) -> Optional[float]:
        """计算执行耗时（秒）
        
        Returns:
            耗时（秒），如果未结束返回None
        """
        if self.end_time is None:
            return None
        return (self.end_time - self.start_time).total_seconds()
    
    # ========== 节点结果管理 ==========
    
    def add_node_result(self, result: NodeExecutionResult) -> None:
        """添加节点执行结果
        
        Args:
            result: 节点执行结果
        """
        self.node_results[result.node_id] = result
    
    def get_node_result(self, node_id: str) -> Optional[NodeExecutionResult]:
        """获取节点执行结果
        
        Args:
            node_id: 节点ID
            
        Returns:
            节点执行结果，如果不存在返回None
        """
        return self.node_results.get(node_id)
    
    # ========== 状态查询 ==========
    
    def get_successful_nodes(self) -> List[str]:
        """获取执行成功的节点列表
        
        Returns:
            成功节点ID列表
        """
        return [
            node_id
            for node_id, result in self.node_results.items()
            if result.status == ExecutionStatus.SUCCESS
        ]
    
    def get_failed_nodes(self) -> List[str]:
        """获取执行失败的节点列表
        
        Returns:
            失败节点ID列表
        """
        return [
            node_id
            for node_id, result in self.node_results.items()
            if result.status == ExecutionStatus.FAILED
        ]
    
    def get_skipped_nodes(self) -> List[str]:
        """获取跳过的节点列表
        
        Returns:
            跳过节点ID列表
        """
        return [
            node_id
            for node_id, result in self.node_results.items()
            if result.status == ExecutionStatus.SKIPPED
        ]
    
    def get_pending_nodes(self) -> List[str]:
        """获取待执行的节点列表
        
        Returns:
            待执行节点ID列表
        """
        return [
            node_id
            for node_id, result in self.node_results.items()
            if result.status == ExecutionStatus.PENDING
        ]
    
    def has_failed_nodes(self) -> bool:
        """检查是否有失败的节点
        
        Returns:
            如果有至少一个节点失败则返回 True
        """
        return len(self.get_failed_nodes()) > 0
    
    def has_successful_nodes(self) -> bool:
        """检查是否有成功的节点
        
        Returns:
            如果有至少一个节点成功则返回 True
        """
        return len(self.get_successful_nodes()) > 0
    
    def is_success(self) -> bool:
        """检查工作流是否执行成功
        
        Returns:
            如果工作流状态为 SUCCESS 则返回 True
        """
        return self.status == ExecutionStatus.SUCCESS
    
    def is_failed(self) -> bool:
        """检查工作流是否执行失败
        
        Returns:
            如果工作流状态为 FAILED 则返回 True
        """
        return self.status == ExecutionStatus.FAILED
    
    # ========== 状态标记 ==========
    
    def mark_started(self) -> None:
        """标记为开始执行"""
        self.status = ExecutionStatus.RUNNING
        self.start_time = datetime.now()
    
    def mark_success(self) -> None:
        """标记为执行成功"""
        self.status = ExecutionStatus.SUCCESS
        self.end_time = datetime.now()
    
    def mark_failed(self) -> None:
        """标记为执行失败"""
        self.status = ExecutionStatus.FAILED
        self.end_time = datetime.now()
    
    def mark_cancelled(self) -> None:
        """标记为已取消"""
        self.status = ExecutionStatus.CANCELLED
        self.end_time = datetime.now()
    
    # ========== 统计信息 ==========
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取执行统计信息
        
        Returns:
            统计信息字典
        """
        total_nodes = len(self.node_results)
        successful = len(self.get_successful_nodes())
        failed = len(self.get_failed_nodes())
        skipped = len(self.get_skipped_nodes())
        pending = len(self.get_pending_nodes())
        
        # 计算平均执行时间
        completed_durations = [
            r.duration
            for r in self.node_results.values()
            if r.duration is not None
        ]
        avg_node_duration = (
            sum(completed_durations) / len(completed_durations)
            if completed_durations else 0
        )
        
        return {
            "total_nodes": total_nodes,
            "successful": successful,
            "failed": failed,
            "skipped": skipped,
            "pending": pending,
            "success_rate": successful / total_nodes if total_nodes > 0 else 0,
            "total_duration": self.duration,
            "avg_node_duration": avg_node_duration
        }
    
    # ========== 序列化 ==========
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典
        
        Returns:
            字典表示
        """
        return {
            "workflow_id": self.workflow_id,
            "execution_id": self.execution_id,
            "status": self.status.value,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration": self.duration,
            "node_results": {
                node_id: result.to_dict()
                for node_id, result in self.node_results.items()
            },
            "statistics": self.get_statistics(),
            "metadata": self.metadata
        }
    
    def __repr__(self) -> str:
        """字符串表示"""
        stats = self.get_statistics()
        return (
            f"WorkflowExecutionResult("
            f"workflow_id='{self.workflow_id}', "
            f"execution_id='{self.execution_id[:8]}...', "
            f"status={self.status.value}, "
            f"nodes={stats['total_nodes']}, "
            f"success={stats['successful']}, "
            f"failed={stats['failed']}, "
            f"duration={self.duration:.2f}s)" if self.duration else f"duration=None)"
        )

