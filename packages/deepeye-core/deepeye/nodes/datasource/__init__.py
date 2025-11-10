"""数据源节点模块

提供各种数据源的节点实现。

所有数据源节点统一输出格式:
- output_ports: ["data"]
- data: pandas.DataFrame
- metadata: 包含数据描述信息
"""

from deepeye.nodes.datasource.base import (
    BaseDataSourceNode,
    DataSourceConfig,
)
from deepeye.nodes.datasource.memory import (
    MemoryDataSourceNode,
    MemoryDataSourceConfig,
)
from deepeye.nodes.datasource.file import (
    FileDataSourceNode,
    FileDataSourceConfig,
)

__all__ = [
    # 基类
    "BaseDataSourceNode",
    "DataSourceConfig",
    
    # 内存数据源
    "MemoryDataSourceNode",
    "MemoryDataSourceConfig",
    
    # 文件数据源
    "FileDataSourceNode",
    "FileDataSourceConfig",
]
