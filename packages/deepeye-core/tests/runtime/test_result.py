"""ExecutionResult 测试"""

import pytest
import time
from datetime import datetime
from deepeye.runtime.result import (
    ExecutionStatus,
    NodeExecutionResult,
    WorkflowExecutionResult
)
from deepeye.nodes.io import NodeOutput


class TestExecutionStatus:
    """ExecutionStatus 测试类"""
    
    def test_is_terminal(self):
        """测试终止状态判断"""
        assert ExecutionStatus.SUCCESS.is_terminal()
        assert ExecutionStatus.FAILED.is_terminal()
        assert ExecutionStatus.SKIPPED.is_terminal()
        assert ExecutionStatus.CANCELLED.is_terminal()
        
        assert not ExecutionStatus.PENDING.is_terminal()
        assert not ExecutionStatus.RUNNING.is_terminal()
    
    def test_is_successful(self):
        """测试成功状态判断"""
        assert ExecutionStatus.SUCCESS.is_successful()
        
        assert not ExecutionStatus.FAILED.is_successful()
        assert not ExecutionStatus.PENDING.is_successful()
        assert not ExecutionStatus.RUNNING.is_successful()
        assert not ExecutionStatus.SKIPPED.is_successful()
        assert not ExecutionStatus.CANCELLED.is_successful()


class TestNodeExecutionResult:
    """NodeExecutionResult 测试类"""
    
    def test_init_default(self):
        """测试默认初始化"""
        result = NodeExecutionResult(node_id="node1")
        
        assert result.node_id == "node1"
        assert result.status == ExecutionStatus.PENDING
        assert result.outputs is None
        assert result.error is None
        assert result.start_time is not None
        assert result.end_time is None
        assert result.duration is None
    
    def test_init_with_params(self):
        """测试带参数初始化"""
        outputs = {"output": NodeOutput()}
        start_time = datetime.now()
        
        result = NodeExecutionResult(
            node_id="node1",
            status=ExecutionStatus.SUCCESS,
            outputs=outputs,
            start_time=start_time,
            metadata={"custom": "data"}
        )
        
        assert result.node_id == "node1"
        assert result.status == ExecutionStatus.SUCCESS
        assert result.outputs is outputs
        assert result.start_time == start_time
        assert result.metadata["custom"] == "data"
    
    def test_duration_calculation(self):
        """测试耗时计算"""
        result = NodeExecutionResult(node_id="node1")
        
        # 未结束时为None
        assert result.duration is None
        
        # 模拟执行
        result.start_time = datetime.now()
        time.sleep(0.1)
        result.end_time = datetime.now()
        
        # 应该大约是0.1秒
        assert result.duration is not None
        assert result.duration >= 0.1
        assert result.duration < 0.2
    
    def test_mark_started(self):
        """测试标记开始"""
        result = NodeExecutionResult(node_id="node1")
        
        result.mark_started()
        
        assert result.status == ExecutionStatus.RUNNING
        assert result.start_time is not None
    
    def test_mark_success(self):
        """测试标记成功"""
        result = NodeExecutionResult(node_id="node1")
        outputs = {"output": NodeOutput(data={"result": 42})}
        
        result.mark_success(outputs)
        
        assert result.status == ExecutionStatus.SUCCESS
        assert result.outputs is outputs
        assert result.end_time is not None
        assert result.duration is not None
    
    def test_mark_failed(self):
        """测试标记失败"""
        result = NodeExecutionResult(node_id="node1")
        error = ValueError("测试错误")
        
        result.mark_failed(error)
        
        assert result.status == ExecutionStatus.FAILED
        assert result.error is error
        assert result.end_time is not None
    
    def test_mark_skipped(self):
        """测试标记跳过"""
        result = NodeExecutionResult(node_id="node1")
        
        result.mark_skipped()
        
        assert result.status == ExecutionStatus.SKIPPED
        assert result.end_time is not None
    
    def test_to_dict(self):
        """测试转换为字典"""
        outputs = {"output": NodeOutput(data={"result": 42})}
        
        result = NodeExecutionResult(node_id="node1")
        result.mark_success(outputs)
        
        data = result.to_dict()
        
        assert data["node_id"] == "node1"
        assert data["status"] == "success"
        assert data["outputs"] is not None
        assert "output" in data["outputs"]
        assert data["start_time"] is not None
        assert data["end_time"] is not None
        assert data["duration"] is not None
    
    def test_to_dict_with_error(self):
        """测试转换为字典（带错误）"""
        result = NodeExecutionResult(node_id="node1")
        result.mark_failed(ValueError("测试错误"))
        
        data = result.to_dict()
        
        assert data["status"] == "failed"
        assert data["error"]["type"] == "ValueError"
        assert data["error"]["message"] == "测试错误"
    
    def test_repr(self):
        """测试字符串表示"""
        result = NodeExecutionResult(node_id="node1")
        result.mark_success(NodeOutput())
        
        repr_str = repr(result)
        
        assert "NodeExecutionResult" in repr_str
        assert "node1" in repr_str
        assert "success" in repr_str


class TestWorkflowExecutionResult:
    """WorkflowExecutionResult 测试类"""
    
    def test_init_default(self):
        """测试默认初始化"""
        result = WorkflowExecutionResult(
            workflow_id="wf-123",
            execution_id="exec-456"
        )
        
        assert result.workflow_id == "wf-123"
        assert result.execution_id == "exec-456"
        assert result.status == ExecutionStatus.PENDING
        assert len(result.node_results) == 0
        assert result.start_time is not None
        assert result.end_time is None
        assert result.duration is None
    
    def test_duration_calculation(self):
        """测试耗时计算"""
        result = WorkflowExecutionResult(
            workflow_id="wf-123",
            execution_id="exec-456"
        )
        
        # 未结束时为None
        assert result.duration is None
        
        # 模拟执行
        result.start_time = datetime.now()
        time.sleep(0.1)
        result.end_time = datetime.now()
        
        # 应该大约是0.1秒
        assert result.duration is not None
        assert result.duration >= 0.1
        assert result.duration < 0.2
    
    def test_add_and_get_node_result(self):
        """测试添加和获取节点结果"""
        wf_result = WorkflowExecutionResult(
            workflow_id="wf-123",
            execution_id="exec-456"
        )
        
        node_result = NodeExecutionResult(node_id="node1", outputs={"output": NodeOutput()})
        wf_result.add_node_result(node_result)
        
        retrieved = wf_result.get_node_result("node1")
        assert retrieved is node_result
    
    def test_get_nonexistent_node_result(self):
        """测试获取不存在的节点结果"""
        result = WorkflowExecutionResult(
            workflow_id="wf-123",
            execution_id="exec-456"
        )
        
        assert result.get_node_result("nonexistent") is None
    
    def test_get_successful_nodes(self):
        """测试获取成功节点列表"""
        wf_result = WorkflowExecutionResult(
            workflow_id="wf-123",
            execution_id="exec-456"
        )
        
        # 添加不同状态的节点
        result1 = NodeExecutionResult(node_id="node1")
        result1.mark_success({"output": NodeOutput()})
        
        result2 = NodeExecutionResult(node_id="node2")
        result2.mark_success({"output": NodeOutput()})
        
        result3 = NodeExecutionResult(node_id="node3")
        result3.mark_failed(ValueError("error"))
        
        wf_result.add_node_result(result1)
        wf_result.add_node_result(result2)
        wf_result.add_node_result(result3)
        
        successful = wf_result.get_successful_nodes()
        
        assert len(successful) == 2
        assert "node1" in successful
        assert "node2" in successful
        assert "node3" not in successful
    
    def test_get_failed_nodes(self):
        """测试获取失败节点列表"""
        wf_result = WorkflowExecutionResult(
            workflow_id="wf-123",
            execution_id="exec-456"
        )
        
        result1 = NodeExecutionResult(node_id="node1")
        result1.mark_success({"output": NodeOutput()})
        
        result2 = NodeExecutionResult(node_id="node2")
        result2.mark_failed(ValueError("error"))
        
        wf_result.add_node_result(result1)
        wf_result.add_node_result(result2)
        
        failed = wf_result.get_failed_nodes()
        
        assert len(failed) == 1
        assert "node2" in failed
    
    def test_get_skipped_nodes(self):
        """测试获取跳过节点列表"""
        wf_result = WorkflowExecutionResult(
            workflow_id="wf-123",
            execution_id="exec-456"
        )
        
        result1 = NodeExecutionResult(node_id="node1")
        result1.mark_skipped()
        
        result2 = NodeExecutionResult(node_id="node2")
        result2.mark_success({"output": NodeOutput()})
        
        wf_result.add_node_result(result1)
        wf_result.add_node_result(result2)
        
        skipped = wf_result.get_skipped_nodes()
        
        assert len(skipped) == 1
        assert "node1" in skipped
    
    def test_get_pending_nodes(self):
        """测试获取待执行节点列表"""
        wf_result = WorkflowExecutionResult(
            workflow_id="wf-123",
            execution_id="exec-456"
        )
        
        result1 = NodeExecutionResult(node_id="node1")  # PENDING
        result2 = NodeExecutionResult(node_id="node2")
        result2.mark_success({"output": NodeOutput()})
        
        wf_result.add_node_result(result1)
        wf_result.add_node_result(result2)
        
        pending = wf_result.get_pending_nodes()
        
        assert len(pending) == 1
        assert "node1" in pending
    
    def test_mark_started(self):
        """测试标记开始"""
        result = WorkflowExecutionResult(
            workflow_id="wf-123",
            execution_id="exec-456"
        )
        
        result.mark_started()
        
        assert result.status == ExecutionStatus.RUNNING
        assert result.start_time is not None
    
    def test_mark_success(self):
        """测试标记成功"""
        result = WorkflowExecutionResult(
            workflow_id="wf-123",
            execution_id="exec-456"
        )
        
        result.mark_success()
        
        assert result.status == ExecutionStatus.SUCCESS
        assert result.end_time is not None
    
    def test_mark_failed(self):
        """测试标记失败"""
        result = WorkflowExecutionResult(
            workflow_id="wf-123",
            execution_id="exec-456"
        )
        
        result.mark_failed()
        
        assert result.status == ExecutionStatus.FAILED
        assert result.end_time is not None
    
    def test_mark_cancelled(self):
        """测试标记取消"""
        result = WorkflowExecutionResult(
            workflow_id="wf-123",
            execution_id="exec-456"
        )
        
        result.mark_cancelled()
        
        assert result.status == ExecutionStatus.CANCELLED
        assert result.end_time is not None
    
    def test_get_statistics(self):
        """测试获取统计信息"""
        wf_result = WorkflowExecutionResult(
            workflow_id="wf-123",
            execution_id="exec-456"
        )
        
        # 添加不同状态的节点
        result1 = NodeExecutionResult(node_id="node1")
        result1.mark_success({"output": NodeOutput()})
        
        result2 = NodeExecutionResult(node_id="node2")
        result2.mark_success({"output": NodeOutput()})
        
        result3 = NodeExecutionResult(node_id="node3")
        result3.mark_failed(ValueError("error"))
        
        result4 = NodeExecutionResult(node_id="node4")
        result4.mark_skipped()
        
        wf_result.add_node_result(result1)
        wf_result.add_node_result(result2)
        wf_result.add_node_result(result3)
        wf_result.add_node_result(result4)
        
        stats = wf_result.get_statistics()
        
        assert stats["total_nodes"] == 4
        assert stats["successful"] == 2
        assert stats["failed"] == 1
        assert stats["skipped"] == 1
        assert stats["pending"] == 0
        assert stats["success_rate"] == 0.5
    
    def test_to_dict(self):
        """测试转换为字典"""
        wf_result = WorkflowExecutionResult(
            workflow_id="wf-123",
            execution_id="exec-456"
        )
        
        node_result = NodeExecutionResult(node_id="node1")
        node_result.mark_success({"output": NodeOutput()})
        wf_result.add_node_result(node_result)
        wf_result.mark_success()
        
        data = wf_result.to_dict()
        
        assert data["workflow_id"] == "wf-123"
        assert data["execution_id"] == "exec-456"
        assert data["status"] == "success"
        assert "node1" in data["node_results"]
        assert "statistics" in data
        assert data["statistics"]["total_nodes"] == 1
    
    def test_repr(self):
        """测试字符串表示"""
        wf_result = WorkflowExecutionResult(
            workflow_id="wf-123",
            execution_id="exec-456"
        )
        
        result1 = NodeExecutionResult(node_id="node1")
        result1.mark_success({"output": NodeOutput()})
        wf_result.add_node_result(result1)
        wf_result.mark_success()
        
        repr_str = repr(wf_result)
        
        assert "WorkflowExecutionResult" in repr_str
        assert "wf-123" in repr_str
        assert "nodes=1" in repr_str
        assert "success=1" in repr_str

