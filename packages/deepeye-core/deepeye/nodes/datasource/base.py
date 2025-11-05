"""数据源节点基类

提供统一的数据源接口，确保所有数据源节点：
1. 输出格式一致（DataFrame + metadata）
2. 易于扩展
3. 标准化的错误处理
"""

from abc import abstractmethod
from typing import Dict, Optional, Any
import pandas as pd

from deepeye.nodes.base import BaseNode, NodeConfig, NodeMetadata
from deepeye.nodes.io import (
    NodeInput,
    NodeOutput,
    NodeOutputPort,
    NodeOutputSchema,
)


class DataSourceConfig(NodeConfig):
    """数据源节点配置基类
    
    所有数据源节点可以继承此类来定义自己的配置结构。
    
    Attributes:
        max_rows: 最大行数限制（防止内存溢出）
        preview_rows: 预览行数
    """
    
    max_rows: int = 100000
    preview_rows: int = 5


class BaseDataSourceNode(BaseNode):
    """数据源节点抽象基类
    
    所有数据源节点应继承此类，并实现 _load_data 方法。
    
    统一输出格式:
    - output_ports: ["data"]
    - data: {"dataframe": pandas.DataFrame}  # 字典包含dataframe字段
    - metadata: {
        "rows": int,           # 行数
        "columns": List[str],  # 列名
        "dtypes": Dict,        # 数据类型
        "source_type": str,    # 数据源类型
        "source_info": Dict    # 数据源特定信息
        "preview": Dict        # 数据预览
      }
    
    设计原则:
    1. 所有数据源输出统一为DataFrame格式
    2. metadata提供详细的数据描述
    3. 子类只需实现_load_data方法
    4. 统一的错误处理和日志
    
    Example:
        >>> class MyDataSourceConfig(DataSourceConfig):
        ...     connection_string: str = ""
        ... 
        >>> class MyDataSourceNode(BaseDataSourceNode):
        ...     node_type = "MyDataSource"
        ...     
        ...     def _parse_config(self, config: Dict[str, Any]) -> MyDataSourceConfig:
        ...         return MyDataSourceConfig(**config)
        ...     
        ...     def _load_data(self) -> pd.DataFrame:
        ...         return pd.DataFrame({"col": [1, 2, 3]})
        ...     
        ...     def _get_source_info(self) -> Dict[str, Any]:
        ...         return {"type": "custom"}
    """
    
    node_type = "BaseDataSource"
    
    def __init__(
        self,
        node_id: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None,
    ):
        """初始化数据源节点
        
        Args:
            node_id: 节点实例ID
            config: 节点配置字典
        """
        super().__init__(node_id, config)
        
        # 设置节点元数据（子类应该覆盖）
        self.metadata = NodeMetadata(
            name=self.node_type,
            display_name="数据源",
            description="从数据源加载数据",
            category="datasource",
            tags=["data", "input"],
            version="0.1.0",
            author="DeepEye"
        )
        
        # 数据源节点通常是根节点，无输入
        self.input_ports = []
        
        # 统一的输出端口
        self.output_ports = [
            NodeOutputPort(
                name="data",
                label="数据输出",
                schemas=[
                    NodeOutputSchema(
                        name="dataframe",
                        type="object",
                        description="输出的数据（DataFrame格式）"
                    )
                ]
            )
        ]
    
    def _parse_config(self, config: Dict[str, Any]) -> DataSourceConfig:
        """解析配置
        
        Args:
            config: 配置字典
            
        Returns:
            DataSourceConfig 对象
        """
        return DataSourceConfig(**config)
    
    def execute(self, inputs: Dict[str, NodeInput]) -> Dict[str, NodeOutput]:
        """执行数据加载
        
        Args:
            inputs: 输入数据（数据源节点通常为空）
        
        Returns:
            包含加载数据的输出字典
        """
        # 调用子类实现的数据加载方法
        df = self._load_data()
        
        # 验证返回类型
        if not isinstance(df, pd.DataFrame):
            return self.create_single_output(
                data=None,
                metadata={
                    "error": f"_load_data() 必须返回 pandas.DataFrame，但返回了 {type(df).__name__}"
                }
            )
        
        # 构建标准化的metadata
        metadata = self._build_metadata(df)
        
        # 返回统一格式的输出
        # 注意：根据输出端口schema定义，data应该是字典 {"dataframe": df}
        return self.create_single_output(
            data={"dataframe": df},
            metadata=metadata
        )
    
    @abstractmethod
    def _load_data(self) -> pd.DataFrame:
        """加载数据（子类必须实现）
        
        Returns:
            加载的数据，必须是pandas.DataFrame格式
        
        Raises:
            NotImplementedError: 子类未实现此方法
        """
        raise NotImplementedError(
            f"{self.__class__.__name__} 必须实现 _load_data() 方法"
        )
    
    def _build_metadata(self, df: pd.DataFrame) -> Dict[str, Any]:
        """构建标准化的metadata
        
        Args:
            df: 加载的DataFrame
        
        Returns:
            标准化的metadata字典
        """
        metadata = {
            # 基础统计信息
            "rows": len(df),
            "columns": list(df.columns),
            "dtypes": {col: str(dtype) for col, dtype in df.dtypes.items()},
            "shape": df.shape,
            
            # 数据源信息
            "source_type": self.node_type,
            "source_info": self._get_source_info(),
            
            # 数据预览
            "preview": self._get_data_preview(df),
        }
        
        return metadata
    
    def _get_source_info(self) -> Dict[str, Any]:
        """获取数据源特定信息（子类可选实现）
        
        Returns:
            数据源的特定信息字典
        """
        return {}
    
    def _get_data_preview(self, df: pd.DataFrame) -> Dict[str, Any]:
        """获取数据预览
        
        Args:
            df: DataFrame
        
        Returns:
            数据预览信息
        """
        preview_rows = self.config.preview_rows if hasattr(self.config, 'preview_rows') else 5
        
        preview = {
            "head": df.head(preview_rows).to_dict(orient="records") if len(df) > 0 else [],
            "shape": df.shape,
        }
        
        # 添加数值列的统计信息
        numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
        if numeric_cols:
            stats = df[numeric_cols].describe().to_dict()
            preview["numeric_stats"] = stats
        
        return preview
    
    def validate_inputs(self, inputs: Dict[str, NodeInput]) -> None:
        """验证输入（数据源节点通常无输入）
        
        Args:
            inputs: 输入数据
        """
        # 数据源节点通常是根节点，不需要输入
        # 允许为空字典
        pass
