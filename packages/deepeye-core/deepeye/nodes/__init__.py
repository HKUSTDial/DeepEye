"""节点系统模块

包含节点的基础类、输入输出定义和注册表。
"""

from deepeye.nodes.base import (
    BaseNode,
    NodeConfig,
    NodeMetadata,
)
from deepeye.nodes.io import (
    NodeInput,
    NodeInputSchema,
    NodeInputPort,
    NodeOutput,
    NodeOutputSchema,
    NodeOutputPort,
    NodeStatus,
)
from deepeye.nodes.registry import (
    NodeRegistry,
    register_node,
    get_registry,
)

__all__ = [
    # Base
    "BaseNode",
    "NodeConfig",
    "NodeMetadata",
    # IO
    "NodeInput",
    "NodeInputSchema",
    "NodeInputPort",
    "NodeOutput",
    "NodeOutputSchema",
    "NodeOutputPort",
    "NodeStatus",
    # Registry
    "NodeRegistry",
    "register_node",
    "get_registry",
]


