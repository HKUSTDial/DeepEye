"""数据转换节点

对DataFrame进行各种转换操作，如重命名列、添加计算列、类型转换等。
"""

from typing import Optional, Dict, List, Any, Union
import pandas as pd

from deepeye.nodes.base import BaseNode
from deepeye.nodes.io import NodeInput, NodeOutput, NodeInputPort, NodeOutputPort


class TransformNode(BaseNode):
    """数据转换节点
    
    支持多种DataFrame转换操作：
    - 列重命名
    - 添加计算列（使用pandas表达式）
    - 删除列
    - 数据类型转换
    - 列值映射/替换
    
    Example:
        >>> # 重命名列
        >>> node = TransformNode(
        ...     node_id="rename",
        ...     rename_columns={"old_name": "new_name"}
        ... )
        
        >>> # 添加计算列
        >>> node = TransformNode(
        ...     node_id="calc",
        ...     add_columns={
        ...         "profit": "revenue - cost",
        ...         "profit_rate": "(revenue - cost) / revenue * 100"
        ...     }
        ... )
        
        >>> # 组合多种操作
        >>> node = TransformNode(
        ...     node_id="transform",
        ...     rename_columns={"amt": "amount"},
        ...     add_columns={"total": "amount * quantity"},
        ...     drop_columns=["temp_col"],
        ...     astype={"amount": "float", "quantity": "int"}
        ... )
    """
    
    node_type = "Transform"
    
    def __init__(
        self,
        node_id: Optional[str] = None,
        rename_columns: Optional[Dict[str, str]] = None,
        add_columns: Optional[Dict[str, str]] = None,
        drop_columns: Optional[List[str]] = None,
        astype: Optional[Dict[str, str]] = None,
        replace_values: Optional[Dict[str, Dict[Any, Any]]] = None,
        **kwargs
    ):
        """初始化转换节点
        
        Args:
            node_id: 节点ID
            rename_columns: 列重命名映射 {旧名: 新名}
            add_columns: 添加计算列 {列名: 计算表达式}
                - 表达式使用pandas.eval语法
                - 可以引用现有列
            drop_columns: 要删除的列名列表
            astype: 类型转换映射 {列名: 目标类型}
                - 支持: "int", "float", "str", "bool", "datetime"
            replace_values: 列值替换 {列名: {旧值: 新值}}
            **kwargs: 其他参数
        
        Raises:
            ValueError: 没有指定任何转换操作
        """
        super().__init__(node_id, **kwargs)
        
        self.rename_columns = rename_columns or {}
        self.add_columns = add_columns or {}
        self.drop_columns = drop_columns or []
        self.astype = astype or {}
        self.replace_values = replace_values or {}
        
        # 验证至少有一个操作
        if not any([
            self.rename_columns,
            self.add_columns,
            self.drop_columns,
            self.astype,
            self.replace_values
        ]):
            raise ValueError(
                "TransformNode必须指定至少一个转换操作 "
                "(rename_columns, add_columns, drop_columns, astype, replace_values)"
            )
        
        # 定义输入输出端口
        self.input_ports = [
            NodeInputPort(
                name="data",
                label="输入数据",
                description="要转换的DataFrame数据",
                required=True
            )
        ]
        
        self.output_ports = [
            NodeOutputPort(
                name="data",
                label="转换后数据",
                description="转换后的DataFrame"
            )
        ]
    
    def execute(self, inputs: Dict[str, NodeInput]) -> Dict[str, NodeOutput]:
        """执行转换操作
        
        Args:
            inputs: 输入数据，包含"data"键
        
        Returns:
            包含转换后数据的输出字典
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
                f"TransformNode期望输入为DataFrame或包含dataframe字段的字典，但得到了{type(data).__name__}"
            )
        
        # 复制DataFrame避免修改原数据
        result_df = df.copy()
        
        # 记录原始信息
        original_columns = list(df.columns)
        original_shape = df.shape
        
        # 执行转换操作
        operations_applied = []
        
        # 1. 重命名列
        if self.rename_columns:
            result_df = self._rename_columns(result_df)
            operations_applied.append(f"renamed {len(self.rename_columns)} columns")
        
        # 2. 添加计算列
        if self.add_columns:
            result_df = self._add_columns(result_df)
            operations_applied.append(f"added {len(self.add_columns)} columns")
        
        # 3. 类型转换
        if self.astype:
            result_df = self._convert_types(result_df)
            operations_applied.append(f"converted {len(self.astype)} column types")
        
        # 4. 值替换
        if self.replace_values:
            result_df = self._replace_values(result_df)
            operations_applied.append(f"replaced values in {len(self.replace_values)} columns")
        
        # 5. 删除列（放在最后，避免影响计算列）
        if self.drop_columns:
            result_df = self._drop_columns(result_df)
            operations_applied.append(f"dropped {len(self.drop_columns)} columns")
        
        # 构建metadata
        metadata = {
            "original_shape": original_shape,
            "result_shape": result_df.shape,
            "original_columns": original_columns,
            "result_columns": list(result_df.columns),
            "operations_applied": operations_applied,
            "columns_added": len(result_df.columns) - len(original_columns) + len(self.drop_columns),
            "columns_removed": len(self.drop_columns),
        }
        
        # 返回结果
        return self.create_single_output(
            data=result_df,
            metadata=metadata
        )
    
    def _rename_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """重命名列
        
        Args:
            df: 输入DataFrame
        
        Returns:
            重命名后的DataFrame
        
        Raises:
            ValueError: 要重命名的列不存在
        """
        # 检查列是否存在
        missing_cols = set(self.rename_columns.keys()) - set(df.columns)
        if missing_cols:
            raise ValueError(
                f"要重命名的列不存在: {missing_cols}\n"
                f"可用的列: {list(df.columns)}"
            )
        
        return df.rename(columns=self.rename_columns)
    
    def _add_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """添加计算列
        
        Args:
            df: 输入DataFrame
        
        Returns:
            添加列后的DataFrame
        
        Raises:
            ValueError: 计算表达式无效
        """
        result_df = df.copy()
        
        for col_name, expression in self.add_columns.items():
            try:
                # 使用pandas.eval计算新列
                result_df[col_name] = result_df.eval(expression)
            except Exception as e:
                raise ValueError(
                    f"添加列 '{col_name}' 失败\n"
                    f"表达式: {expression}\n"
                    f"错误: {e}\n"
                    f"提示: 检查列名是否存在，表达式语法是否正确"
                )
        
        return result_df
    
    def _drop_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """删除列
        
        Args:
            df: 输入DataFrame
        
        Returns:
            删除列后的DataFrame
        
        Raises:
            ValueError: 要删除的列不存在
        """
        # 检查列是否存在
        missing_cols = set(self.drop_columns) - set(df.columns)
        if missing_cols:
            raise ValueError(
                f"要删除的列不存在: {missing_cols}\n"
                f"可用的列: {list(df.columns)}"
            )
        
        return df.drop(columns=self.drop_columns)
    
    def _convert_types(self, df: pd.DataFrame) -> pd.DataFrame:
        """转换数据类型
        
        Args:
            df: 输入DataFrame
        
        Returns:
            类型转换后的DataFrame
        
        Raises:
            ValueError: 列不存在或类型转换失败
        """
        result_df = df.copy()
        
        # 类型映射
        type_mapping = {
            "int": "int64",
            "float": "float64",
            "str": "object",
            "string": "object",
            "bool": "bool",
            "boolean": "bool",
            "datetime": "datetime64[ns]",
        }
        
        for col_name, target_type in self.astype.items():
            if col_name not in result_df.columns:
                raise ValueError(
                    f"要转换类型的列不存在: {col_name}\n"
                    f"可用的列: {list(result_df.columns)}"
                )
            
            # 映射类型名称
            pandas_type = type_mapping.get(target_type.lower(), target_type)
            
            try:
                if pandas_type == "datetime64[ns]":
                    result_df[col_name] = pd.to_datetime(result_df[col_name])
                else:
                    result_df[col_name] = result_df[col_name].astype(pandas_type)
            except Exception as e:
                raise ValueError(
                    f"转换列 '{col_name}' 到类型 '{target_type}' 失败\n"
                    f"错误: {e}"
                )
        
        return result_df
    
    def _replace_values(self, df: pd.DataFrame) -> pd.DataFrame:
        """替换列中的值
        
        Args:
            df: 输入DataFrame
        
        Returns:
            替换值后的DataFrame
        
        Raises:
            ValueError: 列不存在
        """
        result_df = df.copy()
        
        for col_name, value_map in self.replace_values.items():
            if col_name not in result_df.columns:
                raise ValueError(
                    f"要替换值的列不存在: {col_name}\n"
                    f"可用的列: {list(result_df.columns)}"
                )
            
            result_df[col_name] = result_df[col_name].replace(value_map)
        
        return result_df
    
    def get_transform_info(self) -> Dict[str, Any]:
        """获取转换信息
        
        Returns:
            转换配置信息
        """
        return {
            "node_type": self.node_type,
            "rename_columns": self.rename_columns,
            "add_columns": self.add_columns,
            "drop_columns": self.drop_columns,
            "astype": self.astype,
            "replace_values": self.replace_values,
            "operation_count": sum([
                len(self.rename_columns),
                len(self.add_columns),
                len(self.drop_columns),
                len(self.astype),
                len(self.replace_values),
            ]),
        }

