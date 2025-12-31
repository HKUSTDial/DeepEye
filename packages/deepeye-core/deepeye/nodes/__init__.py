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
from deepeye.nodes.utils import (
    deserialize_dataframe,
    deserialize_dataframe_list,
)

# 导入所有节点类以触发自动注册
# 数据源节点
from deepeye.nodes.datasource.memory import MemoryDataSourceNode
from deepeye.nodes.datasource.file import FileDataSourceNode
from deepeye.nodes.database.datasource import DatabaseDataSourceNode

# 处理节点（已移除 FilterNode 和 TransformNode，请使用 DataCoderNode）

# 智能节点
from deepeye.nodes.datacoder.datacoder import DataCoderNode
from deepeye.nodes.dataplot.dataplot import DataPlotNode
from deepeye.nodes.nl2sql.nl2sql import NL2SQLNode
from deepeye.nodes.nl2dv import NL2DVNode

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
    # Utils
    "deserialize_dataframe",
    "deserialize_dataframe_list",
    # 数据源节点
    "MemoryDataSourceNode",
    "FileDataSourceNode",
    "DatabaseDataSourceNode",
    # 处理节点（已移除 FilterNode 和 TransformNode，请使用 DataCoderNode）
    # 智能节点
    "DataCoderNode",
    "DataPlotNode",
    "NL2SQLNode",
    "NL2DVNode",
]


