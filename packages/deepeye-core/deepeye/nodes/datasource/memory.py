"""内存数据源节点

从内存中的Python数据结构加载数据。
适用于测试、示例和小规模数据。
"""

from typing import Optional, Union, List, Dict, Any
import pandas as pd

from deepeye.nodes.base import NodeMetadata
from deepeye.nodes.datasource.base import BaseDataSourceNode, DataSourceConfig


class MemoryDataSourceConfig(DataSourceConfig):
    """内存数据源配置
    
    Attributes:
        data: 数据，支持多种格式
        columns: 列名（仅当data为二维数组时需要）
    """
    
    data: Optional[Union[pd.DataFrame, List, Dict]] = None
    columns: Optional[List[str]] = None


class MemoryDataSourceNode(BaseDataSourceNode):
    """内存数据源节点
    
    从内存中的Python数据结构加载数据，支持：
    - pandas.DataFrame
    - List[Dict] - 记录列表
    - Dict - 单条记录
    - List[List] - 二维数组（需提供列名）
    
    特点:
    - 无需外部依赖
    - 适合测试和示例
    - 性能最快
    - 数据量受内存限制
    
    Example:
        >>> # 从字典列表创建
        >>> node = MemoryDataSourceNode(
        ...     node_id="demo",
        ...     config={
        ...         "data": [
        ...             {"name": "Alice", "age": 25},
        ...             {"name": "Bob", "age": 30}
        ...         ]
        ...     }
        ... )
        >>> result = node.run(inputs={})
        >>> df = result["data"].data["dataframe"]
        >>> print(df)
           name  age
        0  Alice   25
        1    Bob   30
        
        >>> # 从DataFrame创建
        >>> df = pd.DataFrame({"x": [1, 2, 3], "y": [4, 5, 6]})
        >>> node = MemoryDataSourceNode(
        ...     node_id="df",
        ...     config={"data": df}
        ... )
        
        >>> # 从二维数组创建
        >>> node = MemoryDataSourceNode(
        ...     node_id="array",
        ...     config={
        ...         "data": [[1, 2], [3, 4]],
        ...         "columns": ["col1", "col2"]
        ...     }
        ... )
    """
    
    node_type = "MemoryDataSource"
    
    def __init__(
        self,
        node_id: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None,
    ):
        """初始化内存数据源节点
        
        Args:
            node_id: 节点实例ID
            config: 节点配置字典，包含：
                - data: 数据，支持多种格式（DataFrame, List[Dict], Dict, List[List]）
                - columns: 列名（仅当data为二维数组时需要）
                - max_rows: 最大行数限制
                - preview_rows: 预览行数
        
        Raises:
            ValueError: 数据格式不支持
        """
        super().__init__(node_id, config)
        
        # 设置节点元数据
        self.metadata = NodeMetadata(
            name="MemoryDataSource",
            display_name="内存数据源",
            description="从内存中的Python数据结构加载数据",
            category="datasource",
            tags=["memory", "test", "demo"],
            version="0.1.0",
            author="DeepEye"
        )
        
        # 验证数据
        self._validate_data()
    
    def _parse_config(self, config: Dict[str, Any]) -> MemoryDataSourceConfig:
        """解析配置
        
        Args:
            config: 配置字典
            
        Returns:
            MemoryDataSourceConfig 对象
        """
        return MemoryDataSourceConfig(**config)
    
    def _validate_data(self):
        """验证输入数据的有效性"""
        data = self.config.data
        
        if data is None:
            # 允许None，将创建空DataFrame
            return
        
        # 检查数据类型
        valid_types = (pd.DataFrame, list, dict)
        if not isinstance(data, valid_types):
            raise ValueError(
                f"不支持的数据类型: {type(data).__name__}。"
                f"支持的类型: DataFrame, List, Dict"
            )
        
        # 如果是二维数组，必须提供列名
        if isinstance(data, list) and len(data) > 0:
            first_item = data[0]
            if isinstance(first_item, (list, tuple)):
                if self.config.columns is None:
                    raise ValueError(
                        "当data为二维数组时，必须提供columns参数"
                    )
    
    def _load_data(self) -> pd.DataFrame:
        """加载内存数据
        
        Returns:
            DataFrame格式的数据
        """
        data = self.config.data
        
        # 处理None或空数据
        if data is None:
            return pd.DataFrame()
        
        # 已经是DataFrame
        if isinstance(data, pd.DataFrame):
            return data.copy()  # 返回副本，避免修改原数据
        
        # 字典（单条记录）
        if isinstance(data, dict):
            return pd.DataFrame([data])
        
        # 列表
        if isinstance(data, list):
            if len(data) == 0:
                # 空列表
                return pd.DataFrame()
            
            # 记录列表 (List[Dict])
            if isinstance(data[0], dict):
                return pd.DataFrame(data)
            
            # 二维数组 (List[List])
            if isinstance(data[0], (list, tuple)):
                return pd.DataFrame(data, columns=self.config.columns)
            
            # 单列数据 (List[scalar])
            col_name = self.config.columns[0] if self.config.columns else "value"
            return pd.DataFrame({col_name: data})
        
        # 其他情况（理论上不会到达，因为_validate_data已检查）
        raise ValueError(f"无法处理的数据类型: {type(data)}")
    
    def _get_source_info(self) -> Dict[str, Any]:
        """获取数据源信息
        
        Returns:
            数据源的详细信息
        """
        data = self.config.data
        
        info = {
            "source": "memory",
            "data_type": type(data).__name__,
        }
        
        # 添加额外信息
        if isinstance(data, pd.DataFrame):
            info["memory_usage_bytes"] = data.memory_usage(deep=True).sum()
        
        if self.config.columns:
            info["specified_columns"] = self.config.columns
        
        return info
