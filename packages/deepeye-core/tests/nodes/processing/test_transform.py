"""测试TransformNode节点"""

import pytest
import pandas as pd
import numpy as np
from pandas.testing import assert_frame_equal

from deepeye.nodes.processing import TransformNode
from deepeye.nodes.io import NodeInput, NodeStatus


# 测试数据
def create_test_dataframe():
    """创建测试用的DataFrame"""
    return pd.DataFrame({
        "name": ["Alice", "Bob", "Charlie"],
        "age": [25, 30, 28],
        "salary": [50000, 60000, 55000],
        "bonus": [5000, 8000, 6000],
    })


class TestTransformNodeInit:
    """测试TransformNode初始化"""
    
    def test_init_with_rename(self):
        """测试使用重命名初始化"""
        node = TransformNode(
            node_id="test",
            rename_columns={"age": "years"}
        )
        assert node.rename_columns == {"age": "years"}
    
    def test_init_with_add_columns(self):
        """测试使用添加列初始化"""
        node = TransformNode(
            node_id="test",
            add_columns={"total": "salary + bonus"}
        )
        assert node.add_columns == {"total": "salary + bonus"}
    
    def test_init_without_any_operation_raises(self):
        """测试没有任何操作时抛出错误"""
        with pytest.raises(ValueError, match="必须指定至少一个转换操作"):
            TransformNode(node_id="test")


class TestTransformNodeRenameColumns:
    """测试列重命名功能"""
    
    def test_rename_single_column(self):
        """测试重命名单个列"""
        df = create_test_dataframe()
        node = TransformNode(
            node_id="test",
            rename_columns={"age": "years"}
        )
        
        inputs = {"data": NodeInput(data=df)}
        result = node.run(inputs=inputs)
        
        result_df = result["data"].data
        assert "years" in result_df.columns
        assert "age" not in result_df.columns
        assert result_df["years"].tolist() == [25, 30, 28]
    
    def test_rename_multiple_columns(self):
        """测试重命名多个列"""
        df = create_test_dataframe()
        node = TransformNode(
            node_id="test",
            rename_columns={"age": "years", "salary": "income"}
        )
        
        inputs = {"data": NodeInput(data=df)}
        result = node.run(inputs=inputs)
        
        result_df = result["data"].data
        assert "years" in result_df.columns
        assert "income" in result_df.columns
        assert "age" not in result_df.columns
        assert "salary" not in result_df.columns
    
    def test_rename_nonexistent_column_raises(self):
        """测试重命名不存在的列"""
        df = create_test_dataframe()
        node = TransformNode(
            node_id="test",
            rename_columns={"nonexistent": "new_name"}
        )
        
        inputs = {"data": NodeInput(data=df)}
        result = node.run(inputs=inputs)
        
        assert result["data"].status == NodeStatus.FAILED
        assert "不存在" in str(result["data"].error)


class TestTransformNodeAddColumns:
    """测试添加计算列功能"""
    
    def test_add_simple_calculation(self):
        """测试简单计算"""
        df = create_test_dataframe()
        node = TransformNode(
            node_id="test",
            add_columns={"total": "salary + bonus"}
        )
        
        inputs = {"data": NodeInput(data=df)}
        result = node.run(inputs=inputs)
        
        result_df = result["data"].data
        assert "total" in result_df.columns
        assert result_df["total"].tolist() == [55000, 68000, 61000]
    
    def test_add_multiple_columns(self):
        """测试添加多个列"""
        df = create_test_dataframe()
        node = TransformNode(
            node_id="test",
            add_columns={
                "total": "salary + bonus",
                "bonus_rate": "bonus / salary * 100"
            }
        )
        
        inputs = {"data": NodeInput(data=df)}
        result = node.run(inputs=inputs)
        
        result_df = result["data"].data
        assert "total" in result_df.columns
        assert "bonus_rate" in result_df.columns
        assert result_df["total"].tolist() == [55000, 68000, 61000]
    
    def test_add_column_with_invalid_expression_raises(self):
        """测试无效表达式"""
        df = create_test_dataframe()
        node = TransformNode(
            node_id="test",
            add_columns={"invalid": "nonexistent_col * 2"}
        )
        
        inputs = {"data": NodeInput(data=df)}
        result = node.run(inputs=inputs)
        
        assert result["data"].status == NodeStatus.FAILED
        assert "添加列" in str(result["data"].error)


class TestTransformNodeDropColumns:
    """测试删除列功能"""
    
    def test_drop_single_column(self):
        """测试删除单个列"""
        df = create_test_dataframe()
        node = TransformNode(
            node_id="test",
            drop_columns=["bonus"]
        )
        
        inputs = {"data": NodeInput(data=df)}
        result = node.run(inputs=inputs)
        
        result_df = result["data"].data
        assert "bonus" not in result_df.columns
        assert len(result_df.columns) == 3
    
    def test_drop_multiple_columns(self):
        """测试删除多个列"""
        df = create_test_dataframe()
        node = TransformNode(
            node_id="test",
            drop_columns=["bonus", "salary"]
        )
        
        inputs = {"data": NodeInput(data=df)}
        result = node.run(inputs=inputs)
        
        result_df = result["data"].data
        assert "bonus" not in result_df.columns
        assert "salary" not in result_df.columns
        assert set(result_df.columns) == {"name", "age"}
    
    def test_drop_nonexistent_column_raises(self):
        """测试删除不存在的列"""
        df = create_test_dataframe()
        node = TransformNode(
            node_id="test",
            drop_columns=["nonexistent"]
        )
        
        inputs = {"data": NodeInput(data=df)}
        result = node.run(inputs=inputs)
        
        assert result["data"].status == NodeStatus.FAILED


class TestTransformNodeTypeConversion:
    """测试类型转换功能"""
    
    def test_convert_to_int(self):
        """测试转换为整数"""
        df = pd.DataFrame({"col": ["1", "2", "3"]})
        node = TransformNode(
            node_id="test",
            astype={"col": "int"}
        )
        
        inputs = {"data": NodeInput(data=df)}
        result = node.run(inputs=inputs)
        
        result_df = result["data"].data
        assert result_df["col"].dtype == "int64"
        assert result_df["col"].tolist() == [1, 2, 3]
    
    def test_convert_to_float(self):
        """测试转换为浮点数"""
        df = pd.DataFrame({"col": [1, 2, 3]})
        node = TransformNode(
            node_id="test",
            astype={"col": "float"}
        )
        
        inputs = {"data": NodeInput(data=df)}
        result = node.run(inputs=inputs)
        
        result_df = result["data"].data
        assert result_df["col"].dtype == "float64"
    
    def test_convert_to_string(self):
        """测试转换为字符串"""
        df = pd.DataFrame({"col": [1, 2, 3]})
        node = TransformNode(
            node_id="test",
            astype={"col": "str"}
        )
        
        inputs = {"data": NodeInput(data=df)}
        result = node.run(inputs=inputs)
        
        result_df = result["data"].data
        assert result_df["col"].dtype == "object"
        # 注意：astype("object")不会自动转换值的字符串表示，只改变类型
        # 如果需要真正转换为字符串，需要使用 add_columns 或其他方法
    
    def test_convert_nonexistent_column_raises(self):
        """测试转换不存在的列"""
        df = create_test_dataframe()
        node = TransformNode(
            node_id="test",
            astype={"nonexistent": "int"}
        )
        
        inputs = {"data": NodeInput(data=df)}
        result = node.run(inputs=inputs)
        
        assert result["data"].status == NodeStatus.FAILED


class TestTransformNodeReplaceValues:
    """测试值替换功能"""
    
    def test_replace_values_in_column(self):
        """测试替换列中的值"""
        df = pd.DataFrame({
            "status": ["active", "inactive", "active"],
            "value": [1, 2, 3]
        })
        node = TransformNode(
            node_id="test",
            replace_values={
                "status": {"active": "A", "inactive": "I"}
            }
        )
        
        inputs = {"data": NodeInput(data=df)}
        result = node.run(inputs=inputs)
        
        result_df = result["data"].data
        assert result_df["status"].tolist() == ["A", "I", "A"]
    
    def test_replace_values_in_multiple_columns(self):
        """测试替换多个列的值"""
        df = pd.DataFrame({
            "col1": ["A", "B", "C"],
            "col2": [1, 2, 3]
        })
        node = TransformNode(
            node_id="test",
            replace_values={
                "col1": {"A": "X", "B": "Y"},
                "col2": {1: 10, 2: 20}
            }
        )
        
        inputs = {"data": NodeInput(data=df)}
        result = node.run(inputs=inputs)
        
        result_df = result["data"].data
        assert result_df["col1"].tolist() == ["X", "Y", "C"]
        assert result_df["col2"].tolist() == [10, 20, 3]


class TestTransformNodeCombined:
    """测试组合操作"""
    
    def test_rename_and_add(self):
        """测试重命名和添加列"""
        df = create_test_dataframe()
        node = TransformNode(
            node_id="test",
            rename_columns={"salary": "income"},
            add_columns={"total": "income + bonus"}
        )
        
        inputs = {"data": NodeInput(data=df)}
        result = node.run(inputs=inputs)
        
        result_df = result["data"].data
        assert "income" in result_df.columns
        assert "total" in result_df.columns
        assert "salary" not in result_df.columns
    
    def test_add_and_drop(self):
        """测试添加后删除列"""
        df = create_test_dataframe()
        node = TransformNode(
            node_id="test",
            add_columns={"total": "salary + bonus"},
            drop_columns=["salary", "bonus"]
        )
        
        inputs = {"data": NodeInput(data=df)}
        result = node.run(inputs=inputs)
        
        result_df = result["data"].data
        assert "total" in result_df.columns
        assert "salary" not in result_df.columns
        assert "bonus" not in result_df.columns
    
    def test_all_operations_combined(self):
        """测试所有操作组合"""
        df = create_test_dataframe()
        node = TransformNode(
            node_id="test",
            rename_columns={"salary": "income"},
            add_columns={"total": "income + bonus"},
            astype={"age": "str"},
            replace_values={"name": {"Alice": "Alice Smith"}},
            drop_columns=["bonus"]
        )
        
        inputs = {"data": NodeInput(data=df)}
        result = node.run(inputs=inputs)
        
        result_df = result["data"].data
        assert "income" in result_df.columns
        assert "total" in result_df.columns
        assert "bonus" not in result_df.columns
        assert result_df["age"].dtype == "object"
        assert result_df["name"].iloc[0] == "Alice Smith"


class TestTransformNodeMetadata:
    """测试metadata生成"""
    
    def test_metadata_basic_info(self):
        """测试metadata包含基本信息"""
        df = create_test_dataframe()
        node = TransformNode(
            node_id="test",
            add_columns={"total": "salary + bonus"}
        )
        
        inputs = {"data": NodeInput(data=df)}
        result = node.run(inputs=inputs)
        
        metadata = result["data"].metadata
        assert metadata["original_shape"] == (3, 4)
        assert metadata["result_shape"] == (3, 5)
        assert "operations_applied" in metadata
        assert metadata["columns_added"] == 1
    
    def test_metadata_operations_applied(self):
        """测试操作记录"""
        df = create_test_dataframe()
        node = TransformNode(
            node_id="test",
            rename_columns={"age": "years"},
            add_columns={"total": "salary + bonus"},
            drop_columns=["bonus"]
        )
        
        inputs = {"data": NodeInput(data=df)}
        result = node.run(inputs=inputs)
        
        metadata = result["data"].metadata
        operations = metadata["operations_applied"]
        assert any("renamed" in op for op in operations)
        assert any("added" in op for op in operations)
        assert any("dropped" in op for op in operations)


class TestTransformNodeEdgeCases:
    """测试边界情况"""
    
    def test_with_empty_dataframe(self):
        """测试空DataFrame"""
        df = pd.DataFrame(columns=["col1", "col2"])
        node = TransformNode(
            node_id="test",
            add_columns={"col3": "col1 + col2"}
        )
        
        inputs = {"data": NodeInput(data=df)}
        result = node.run(inputs=inputs)
        
        result_df = result["data"].data
        assert "col3" in result_df.columns
        assert len(result_df) == 0
    
    def test_with_non_dataframe_raises(self):
        """测试非DataFrame输入"""
        node = TransformNode(
            node_id="test",
            rename_columns={"col": "new_col"}
        )
        
        inputs = {"data": NodeInput(data=[1, 2, 3])}
        result = node.run(inputs=inputs)
        
        assert result["data"].status == NodeStatus.FAILED
        assert "期望输入为DataFrame" in str(result["data"].error)
    
    def test_get_transform_info(self):
        """测试获取转换信息"""
        node = TransformNode(
            node_id="test",
            rename_columns={"a": "b"},
            add_columns={"c": "a + b"}
        )
        
        info = node.get_transform_info()
        assert info["rename_columns"] == {"a": "b"}
        assert info["add_columns"] == {"c": "a + b"}
        assert info["operation_count"] == 2


class TestTransformNodeIntegration:
    """集成测试"""
    
    def test_data_pipeline(self):
        """测试数据处理流水线"""
        df = create_test_dataframe()
        
        # 第一步：添加总收入列
        transform1 = TransformNode(
            node_id="add_total",
            add_columns={"total_income": "salary + bonus"}
        )
        inputs1 = {"data": NodeInput(data=df)}
        result1 = transform1.run(inputs=inputs1)
        df1 = result1["data"].data
        
        # 第二步：删除原始列
        transform2 = TransformNode(
            node_id="cleanup",
            drop_columns=["salary", "bonus"]
        )
        inputs2 = {"data": NodeInput(data=df1)}
        result2 = transform2.run(inputs=inputs2)
        df2 = result2["data"].data
        
        assert "total_income" in df2.columns
        assert "salary" not in df2.columns
        assert "bonus" not in df2.columns
    
    def test_reset_and_reexecute(self):
        """测试重置后重新执行"""
        df = create_test_dataframe()
        node = TransformNode(
            node_id="test",
            add_columns={"total": "salary + bonus"}
        )
        
        inputs = {"data": NodeInput(data=df)}
        
        # 第一次执行
        result1 = node.run(inputs=inputs)
        df1 = result1["data"].data
        
        # 重置
        node.reset()
        
        # 第二次执行
        result2 = node.run(inputs=inputs)
        df2 = result2["data"].data
        
        # 两次结果应该相同
        assert_frame_equal(df1, df2)

