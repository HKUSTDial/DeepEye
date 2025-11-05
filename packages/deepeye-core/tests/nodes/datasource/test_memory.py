"""测试MemoryDataSourceNode节点"""

import pytest
import pandas as pd
from pandas.testing import assert_frame_equal
from pydantic import ValidationError

from deepeye.nodes.datasource import MemoryDataSourceNode
from deepeye.nodes.io import NodeStatus


class TestMemoryDataSourceNode:
    """测试MemoryDataSourceNode基本功能"""
    
    def test_init_with_dataframe(self):
        """测试使用DataFrame初始化"""
        df = pd.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6]})
        node = MemoryDataSourceNode(node_id="test", config={"data": df})
        
        assert node.node_id == "test"
        assert node.node_type == "MemoryDataSource"
        assert len(node.input_ports) == 0  # 数据源无输入
        assert len(node.output_ports) == 1
        assert node.output_ports[0].name == "data"
    
    def test_init_with_dict_list(self):
        """测试使用字典列表初始化"""
        data = [
            {"name": "Alice", "age": 25},
            {"name": "Bob", "age": 30},
        ]
        node = MemoryDataSourceNode(node_id="test", config={"data": data})
        assert node.config.data == data
    
    def test_init_with_single_dict(self):
        """测试使用单个字典初始化"""
        data = {"name": "Alice", "age": 25}
        node = MemoryDataSourceNode(node_id="test", config={"data": data})
        assert node.config.data == data
    
    def test_init_with_2d_array_and_columns(self):
        """测试使用二维数组和列名初始化"""
        data = [[1, 2], [3, 4]]
        columns = ["col1", "col2"]
        node = MemoryDataSourceNode(node_id="test", config={"data": data, "columns": columns})
        assert node.config.data == data
        assert node.config.columns == columns
    
    def test_init_with_2d_array_without_columns_raises(self):
        """测试二维数组缺少列名时抛出错误"""
        data = [[1, 2], [3, 4]]
        with pytest.raises(ValueError, match="必须提供columns参数"):
            MemoryDataSourceNode(node_id="test", config={"data": data})
    
    def test_init_with_none(self):
        """测试使用None初始化（创建空数据源）"""
        node = MemoryDataSourceNode(node_id="test", config={"data": None})
        assert node.config.data is None
    
    def test_init_with_invalid_type_raises(self):
        """测试使用不支持的类型初始化时抛出错误"""
        with pytest.raises(ValidationError):
            MemoryDataSourceNode(node_id="test", config={"data": "invalid"})


class TestMemoryDataSourceExecution:
    """测试MemoryDataSourceNode的执行"""
    
    def test_execute_with_dataframe(self):
        """测试执行：DataFrame输入"""
        df = pd.DataFrame({"x": [1, 2, 3], "y": [4, 5, 6]})
        node = MemoryDataSourceNode(node_id="test", config={"data": df})
        
        result = node.run(inputs={})
        
        assert "data" in result
        output = result["data"]
        assert output.status == NodeStatus.SUCCESS
        assert isinstance(output.data, dict)
        assert "dataframe" in output.data
        assert isinstance(output.data["dataframe"], pd.DataFrame)
        assert_frame_equal(output.data["dataframe"], df)
        
        # 验证metadata
        metadata = output.metadata
        assert metadata["rows"] == 3
        assert metadata["columns"] == ["x", "y"]
        assert "dtypes" in metadata
        assert metadata["source_type"] == "MemoryDataSource"
    
    def test_execute_with_dict_list(self):
        """测试执行：字典列表输入"""
        data = [
            {"name": "Alice", "age": 25, "city": "Beijing"},
            {"name": "Bob", "age": 30, "city": "Shanghai"},
        ]
        node = MemoryDataSourceNode(node_id="test", config={"data": data})
        
        result = node.run(inputs={})
        output = result["data"]
        
        assert output.status == NodeStatus.SUCCESS
        df = output.data["dataframe"]
        assert len(df) == 2
        assert list(df.columns) == ["name", "age", "city"]
        assert df.loc[0, "name"] == "Alice"
        assert df.loc[1, "age"] == 30
    
    def test_execute_with_single_dict(self):
        """测试执行：单个字典输入（单行）"""
        data = {"name": "Alice", "age": 25, "city": "Beijing"}
        node = MemoryDataSourceNode(node_id="test", config={"data": data})
        
        result = node.run(inputs={})
        output = result["data"]
        
        df = output.data["dataframe"]
        assert len(df) == 1
        assert df.loc[0, "name"] == "Alice"
    
    def test_execute_with_2d_array(self):
        """测试执行：二维数组输入"""
        data = [[1, 2, 3], [4, 5, 6]]
        columns = ["a", "b", "c"]
        node = MemoryDataSourceNode(node_id="test", config={"data": data, "columns": columns})
        
        result = node.run(inputs={})
        output = result["data"]
        
        df = output.data["dataframe"]
        assert len(df) == 2
        assert list(df.columns) == ["a", "b", "c"]
        assert df.loc[0, "a"] == 1
        assert df.loc[1, "c"] == 6
    
    def test_execute_with_1d_array(self):
        """测试执行：一维数组输入（单列）"""
        data = [1, 2, 3, 4, 5]
        node = MemoryDataSourceNode(node_id="test", config={"data": data})
        
        result = node.run(inputs={})
        output = result["data"]
        
        df = output.data["dataframe"]
        assert len(df) == 5
        assert "value" in df.columns  # 默认列名
        assert df["value"].tolist() == data
    
    def test_execute_with_1d_array_custom_column(self):
        """测试执行：一维数组带自定义列名"""
        data = [10, 20, 30]
        columns = ["score"]
        node = MemoryDataSourceNode(node_id="test", config={"data": data, "columns": columns})
        
        result = node.run(inputs={})
        df = result["data"].data["dataframe"]
        
        assert "score" in df.columns
        assert df["score"].tolist() == data
    
    def test_execute_with_empty_list(self):
        """测试执行：空列表"""
        node = MemoryDataSourceNode(node_id="test", config={"data": []})
        
        result = node.run(inputs={})
        df = result["data"].data["dataframe"]
        
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 0
    
    def test_execute_with_none(self):
        """测试执行：None数据（空DataFrame）"""
        node = MemoryDataSourceNode(node_id="test", config={"data": None})
        
        result = node.run(inputs={})
        df = result["data"].data["dataframe"]
        
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 0
    
    def test_dataframe_copy(self):
        """测试返回的DataFrame是副本（不修改原数据）"""
        original_df = pd.DataFrame({"x": [1, 2, 3]})
        node = MemoryDataSourceNode(node_id="test", config={"data": original_df})
        
        result = node.run(inputs={})
        returned_df = result["data"].data["dataframe"]
        
        # 修改返回的DataFrame
        returned_df.loc[0, "x"] = 999
        
        # 原始数据不应被修改
        assert original_df.loc[0, "x"] == 1


class TestMemoryDataSourceMetadata:
    """测试metadata的生成"""
    
    def test_metadata_basic_info(self):
        """测试metadata包含基本信息"""
        data = [{"a": 1, "b": 2}, {"a": 3, "b": 4}]
        node = MemoryDataSourceNode(node_id="test", config={"data": data})
        
        result = node.run(inputs={})
        metadata = result["data"].metadata
        
        # 基础信息
        assert metadata["rows"] == 2
        assert metadata["columns"] == ["a", "b"]
        assert "dtypes" in metadata
        
        # 数据源信息
        assert metadata["source_type"] == "MemoryDataSource"
        assert "source_info" in metadata
        assert metadata["source_info"]["source"] == "memory"
    
    def test_metadata_preview(self):
        """测试metadata包含数据预览"""
        data = [{"x": i} for i in range(10)]
        node = MemoryDataSourceNode(node_id="test", config={"data": data})
        
        result = node.run(inputs={})
        metadata = result["data"].metadata
        
        preview = metadata["preview"]
        assert "head" in preview
        assert len(preview["head"]) == 5  # 默认预览5行
        assert "shape" in preview
        assert preview["shape"] == (10, 1)
    
    def test_metadata_numeric_stats(self):
        """测试metadata包含数值列统计信息"""
        data = pd.DataFrame({
            "score": [85, 90, 78, 92, 88],
            "age": [20, 22, 21, 23, 20]
        })
        node = MemoryDataSourceNode(node_id="test", config={"data": data})
        
        result = node.run(inputs={})
        metadata = result["data"].metadata
        
        assert "numeric_stats" in metadata["preview"]
        stats = metadata["preview"]["numeric_stats"]
        assert "score" in stats
        assert "age" in stats


class TestMemoryDataSourceIntegration:
    """集成测试"""
    
    def test_use_in_workflow(self):
        """测试在工作流中使用（模拟场景）"""
        # 创建数据源节点
        data = [
            {"product": "A", "price": 100, "quantity": 5},
            {"product": "B", "price": 200, "quantity": 3},
            {"product": "C", "price": 150, "quantity": 4},
        ]
        source_node = MemoryDataSourceNode(node_id="source", config={"data": data})
        
        # 执行
        result = source_node.run(inputs={})
        
        # 验证输出可以作为下游节点的输入
        df = result["data"].data["dataframe"]
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 3
        assert set(df.columns) == {"product", "price", "quantity"}
        
        # 模拟下游节点处理
        total_value = (df["price"] * df["quantity"]).sum()
        assert total_value == 100*5 + 200*3 + 150*4
    
    def test_multiple_executions(self):
        """测试多次执行"""
        node = MemoryDataSourceNode(
            node_id="test",
            config={"data": [{"x": i} for i in range(5)]}
        )
        
        # 第一次执行
        result1 = node.run(inputs={})
        df1 = result1["data"].data["dataframe"]
        
        # 重置节点
        node.reset()
        
        # 第二次执行
        result2 = node.run(inputs={})
        df2 = result2["data"].data["dataframe"]
        
        # 两次结果应该相同
        assert_frame_equal(df1, df2)

