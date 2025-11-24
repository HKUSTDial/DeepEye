"""节点工具函数

提供节点开发中常用的工具函数。
"""

from typing import Any, Optional
import pandas as pd


def deserialize_dataframe(data: Any) -> Optional[pd.DataFrame]:
    """将序列化的 DataFrame 转换回 pandas.DataFrame
    
    支持多种输入格式：
    1. pandas.DataFrame - 直接返回
    2. 序列化的 DataFrame 字典 - {type: "DataFrame", preview: [...]}
    3. 普通字典 - 尝试转换为 DataFrame
    4. 列表 - 尝试转换为 DataFrame
    
    Args:
        data: 可能是 DataFrame、字典、列表或其他类型
        
    Returns:
        pandas.DataFrame 或 None（如果无法转换）
        
    Examples:
        >>> # 已经是 DataFrame
        >>> df = pd.DataFrame({'a': [1, 2, 3]})
        >>> result = deserialize_dataframe(df)
        >>> assert result is df
        
        >>> # 序列化的 DataFrame
        >>> serialized = {
        ...     "type": "DataFrame",
        ...     "shape": [3, 1],
        ...     "columns": ["a"],
        ...     "preview": [{"a": 1}, {"a": 2}, {"a": 3}]
        ... }
        >>> result = deserialize_dataframe(serialized)
        >>> assert isinstance(result, pd.DataFrame)
        
        >>> # 普通字典
        >>> data = {"a": [1, 2, 3], "b": [4, 5, 6]}
        >>> result = deserialize_dataframe(data)
        >>> assert isinstance(result, pd.DataFrame)
        
        >>> # 列表
        >>> data = [{"a": 1, "b": 4}, {"a": 2, "b": 5}]
        >>> result = deserialize_dataframe(data)
        >>> assert isinstance(result, pd.DataFrame)
    """
    # 如果已经是 DataFrame，直接返回
    if isinstance(data, pd.DataFrame):
        return data
    
    # 如果是字典格式
    if isinstance(data, dict):
        # 检查是否是序列化的 DataFrame（后端序列化格式）
        if data.get("type") == "DataFrame" and "preview" in data:
            try:
                # 从 preview 重建 DataFrame
                return pd.DataFrame(data["preview"])
            except Exception as e:
                print(f"⚠️  无法从序列化数据重建 DataFrame: {e}")
                return None
        
        # 尝试直接从字典创建 DataFrame
        try:
            return pd.DataFrame(data)
        except Exception:
            return None
    
    # 如果是列表，尝试创建 DataFrame
    if isinstance(data, list):
        try:
            return pd.DataFrame(data)
        except Exception:
            return None
    
    return None


def deserialize_dataframe_list(data_list: Any) -> Optional[list[pd.DataFrame]]:
    """将序列化的 DataFrame 列表转换回 pandas.DataFrame 列表
    
    Args:
        data_list: DataFrame 列表或序列化的 DataFrame 列表
        
    Returns:
        pandas.DataFrame 列表或 None（如果无法转换）
        
    Examples:
        >>> data_list = [
        ...     {"type": "DataFrame", "preview": [{"a": 1}]},
        ...     {"type": "DataFrame", "preview": [{"b": 2}]}
        ... ]
        >>> result = deserialize_dataframe_list(data_list)
        >>> assert len(result) == 2
        >>> assert all(isinstance(df, pd.DataFrame) for df in result)
    """
    if not isinstance(data_list, list):
        return None
    
    result = []
    for i, data in enumerate(data_list):
        df = deserialize_dataframe(data)
        if df is None:
            print(f"⚠️  无法转换列表中的第 {i} 个元素为 DataFrame")
            return None
        result.append(df)
    
    return result

