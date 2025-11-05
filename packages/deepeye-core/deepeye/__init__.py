"""
DeepEye Core SDK

一个可视化驱动的数据智能体编排引擎。

Example:
    >>> from deepeye import WorkflowBuilder, WorkflowExecutor
    >>> from deepeye.nodes import DataSourceNode, NL2SQLNode
    >>> 
    >>> workflow = WorkflowBuilder() \\
    ...     .add_node("datasource", DataSourceNode()) \\
    ...     .add_node("nl2sql", NL2SQLNode()) \\
    ...     .add_edge("datasource", "nl2sql") \\
    ...     .build()
    >>> 
    >>> executor = WorkflowExecutor()
    >>> result = executor.execute(workflow)
"""

from deepeye.__version__ import __version__, __author__, __email__, __license__

# 核心导出
from deepeye.nodes import BaseNode

# Workflow (Phase 2 已完成)
from deepeye.workflow import Workflow, WorkflowGraph

# Runtime (Phase 3 已完成)
from deepeye.runtime import WorkflowExecutor

__all__ = [
    "__version__",
    "__author__",
    "__email__",
    "__license__",
    "BaseNode",
    "Workflow",
    "WorkflowGraph",
    "WorkflowExecutor",
]

