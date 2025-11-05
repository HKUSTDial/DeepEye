"""数据过滤节点

根据条件表达式过滤数据行，可选地选择特定列。
"""

from typing import Optional, List, Dict, Any
import pandas as pd

from deepeye.nodes.base import BaseNode
from deepeye.nodes.io import NodeInput, NodeOutput, NodeInputPort, NodeOutputPort


class FilterNode(BaseNode):
    """数据过滤节点
    
    主要功能：根据条件表达式过滤数据行
    辅助功能：选择特定列（可选）
    
    条件表达式使用pandas.query语法，支持：
    - 比较操作符: >, <, >=, <=, ==, !=
    - 逻辑操作符: and, or, not, &, |, ~
    - 成员测试: in, not in
    - 字符串方法: .str.contains(), .str.startswith(), etc.
    
    Example:
        >>> # 简单条件
        >>> filter_node = FilterNode(
        ...     node_id="filter1",
        ...     condition="age > 25"
        ... )
        
        >>> # 多条件
        >>> filter_node = FilterNode(
        ...     node_id="filter2",
        ...     condition="age > 25 and city == 'Beijing'"
        ... )
        
        >>> # 带列选择
        >>> filter_node = FilterNode(
        ...     node_id="filter3",
        ...     condition="score >= 90",
        ...     columns=["name", "score"]  # 只保留这些列
        ... )
        
        >>> # 只做列选择（不过滤行）
        >>> filter_node = FilterNode(
        ...     node_id="select",
        ...     columns=["name", "age"]  # condition为None
        ... )
    """
    
    node_type = "Filter"
    
    def __init__(
        self,
        node_id: Optional[str] = None,
        condition: Optional[str] = None,
        columns: Optional[List[str]] = None,
        **kwargs
    ):
        """初始化过滤节点
        
        Args:
            node_id: 节点ID
            condition: 过滤条件表达式（pandas.query语法）
                - None表示不过滤行，保留所有行
                - 空字符串等同于None
            columns: 要保留的列名列表
                - None表示保留所有列
                - []（空列表）会报错
            **kwargs: 其他参数
        
        Raises:
            ValueError: 条件和列都为空，或列列表为空
        """
        super().__init__(node_id, **kwargs)
        
        # 处理空字符串
        self.condition = condition if condition and condition.strip() else None
        self.columns = columns
        
        # 验证参数
        self._validate_params()
        
        # 定义输入输出端口
        self.input_ports = [
            NodeInputPort(
                name="data",
                label="输入数据",
                description="要过滤的DataFrame数据",
                required=True
            )
        ]
        
        self.output_ports = [
            NodeOutputPort(
                name="data",
                label="过滤后数据",
                description="过滤和/或列选择后的DataFrame"
            )
        ]
    
    def _validate_params(self):
        """验证参数"""
        # 至少要有条件或列选择之一
        if self.condition is None and self.columns is None:
            raise ValueError(
                "FilterNode必须指定condition（行过滤）或columns（列选择）中的至少一个"
            )
        
        # 列列表不能为空列表（但可以是None）
        if self.columns is not None and len(self.columns) == 0:
            raise ValueError("columns不能为空列表，应该为None或包含至少一列")
    
    def execute(self, inputs: Dict[str, NodeInput]) -> Dict[str, NodeOutput]:
        """执行过滤操作
        
        Args:
            inputs: 输入数据，包含"data"键
        
        Returns:
            包含过滤后数据的输出字典
        """
        # 获取输入数据
        input_data = self.get_single_input(inputs)
        data = input_data.data
        
        # 如果输入是字典（来自数据源节点），提取dataframe字段
        if isinstance(data, dict) and "dataframe" in data:
            df = data["dataframe"]
        else:
            df = data
        
        if not isinstance(df, pd.DataFrame):
            raise TypeError(
                f"FilterNode期望输入为DataFrame或包含dataframe字段的字典，但得到了{type(data).__name__}"
            )
        
        # 记录原始数据信息
        original_rows = len(df)
        original_cols = len(df.columns)
        
        # 执行过滤
        filtered_df = self._apply_filter(df)
        
        # 执行列选择
        result_df = self._select_columns(filtered_df)
        
        # 记录结果信息
        result_rows = len(result_df)
        result_cols = len(result_df.columns)
        
        # 构建metadata
        metadata = {
            "original_shape": (original_rows, original_cols),
            "result_shape": (result_rows, result_cols),
            "rows_filtered": original_rows - result_rows,
            "columns_selected": result_cols,
            "filter_rate": 1 - (result_rows / original_rows) if original_rows > 0 else 0,
            "condition": self.condition,
            "columns": self.columns,
        }
        
        # 返回结果
        return self.create_single_output(
            data=result_df,
            metadata=metadata
        )
    
    def _apply_filter(self, df: pd.DataFrame) -> pd.DataFrame:
        """应用行过滤
        
        Args:
            df: 输入DataFrame
        
        Returns:
            过滤后的DataFrame
        
        Raises:
            ValueError: 条件表达式无效
        """
        if self.condition is None:
            # 没有过滤条件，返回所有行
            return df
        
        try:
            # 使用pandas.query进行过滤
            filtered = df.query(self.condition)
            return filtered
        except Exception as e:
            raise ValueError(
                f"过滤条件无效: '{self.condition}'\n"
                f"错误: {e}\n"
                f"提示: 请检查列名是否存在，表达式语法是否正确"
            )
    
    def _select_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """选择指定列
        
        Args:
            df: 输入DataFrame
        
        Returns:
            选择列后的DataFrame
        
        Raises:
            ValueError: 指定的列不存在
        """
        if self.columns is None:
            # 没有列选择，返回所有列
            return df
        
        # 检查列是否存在
        missing_cols = set(self.columns) - set(df.columns)
        if missing_cols:
            raise ValueError(
                f"以下列不存在于数据中: {missing_cols}\n"
                f"可用的列: {list(df.columns)}"
            )
        
        # 选择列
        return df[self.columns]
    
    def get_filter_info(self) -> Dict[str, Any]:
        """获取过滤器信息
        
        Returns:
            过滤器配置信息
        """
        return {
            "node_type": self.node_type,
            "condition": self.condition,
            "columns": self.columns,
            "has_row_filter": self.condition is not None,
            "has_column_select": self.columns is not None,
        }


class RowFilterNode(FilterNode):
    """行过滤节点的便捷类
    
    仅做行过滤，不选择列。
    
    Example:
        >>> filter_node = RowFilterNode(
        ...     node_id="row_filter",
        ...     condition="age > 25 and score >= 90"
        ... )
    """
    
    def __init__(
        self,
        node_id: Optional[str] = None,
        condition: str = None,
        **kwargs
    ):
        if not condition:
            raise ValueError("RowFilterNode必须指定condition参数")
        
        # 强制columns为None
        super().__init__(
            node_id=node_id,
            condition=condition,
            columns=None,
            **kwargs
        )


class ColumnSelectNode(FilterNode):
    """列选择节点的便捷类
    
    仅做列选择，不过滤行。
    
    Example:
        >>> select_node = ColumnSelectNode(
        ...     node_id="select",
        ...     columns=["name", "age", "score"]
        ... )
    """
    
    def __init__(
        self,
        node_id: Optional[str] = None,
        columns: List[str] = None,
        **kwargs
    ):
        if not columns:
            raise ValueError("ColumnSelectNode必须指定columns参数")
        
        # 强制condition为None
        super().__init__(
            node_id=node_id,
            condition=None,
            columns=columns,
            **kwargs
        )

