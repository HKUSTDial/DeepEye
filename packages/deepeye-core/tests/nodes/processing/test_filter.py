"""测试FilterNode节点"""

import pytest
import pandas as pd
from pandas.testing import assert_frame_equal

from deepeye.nodes.processing import FilterNode, RowFilterNode, ColumnSelectNode
from deepeye.nodes.io import NodeInput, NodeStatus


# 测试数据
def create_test_dataframe():
    """创建测试用的DataFrame"""
    return pd.DataFrame({
        "name": ["Alice", "Bob", "Charlie", "David", "Eve"],
        "age": [25, 30, 28, 35, 27],
        "city": ["Beijing", "Shanghai", "Beijing", "Shenzhen", "Shanghai"],
        "score": [95, 87, 92, 88, 90],
    })


class TestFilterNode:
    """测试FilterNode基本功能"""
    
    def test_init_with_condition(self):
        """测试使用条件初始化"""
        node = FilterNode(node_id="test", condition="age > 25")
        assert node.node_id == "test"
        assert node.node_type == "Filter"
        assert node.condition == "age > 25"
        assert node.columns is None
    
    def test_init_with_columns(self):
        """测试使用列选择初始化"""
        node = FilterNode(node_id="test", columns=["name", "age"])
        assert node.condition is None
        assert node.columns == ["name", "age"]
    
    def test_init_with_both(self):
        """测试同时使用条件和列选择"""
        node = FilterNode(
            node_id="test",
            condition="age > 25",
            columns=["name", "age"]
        )
        assert node.condition == "age > 25"
        assert node.columns == ["name", "age"]
    
    def test_init_without_any_raises(self):
        """测试既无条件也无列选择时抛出错误"""
        with pytest.raises(ValueError, match="必须指定condition"):
            FilterNode(node_id="test")
    
    def test_init_with_empty_columns_raises(self):
        """测试空列列表抛出错误"""
        with pytest.raises(ValueError, match="columns不能为空列表"):
            FilterNode(node_id="test", columns=[])
    
    def test_init_with_empty_string_condition(self):
        """测试空字符串条件被视为None"""
        node = FilterNode(node_id="test", condition="  ", columns=["name"])
        assert node.condition is None


class TestFilterNodeRowFiltering:
    """测试行过滤功能"""
    
    def test_execute_simple_condition(self):
        """测试简单条件过滤"""
        df = create_test_dataframe()
        node = FilterNode(node_id="test", condition="age > 27")
        
        inputs = {"data": NodeInput(data=df)}
        result = node.run(inputs=inputs)
        
        output = result["data"]
        assert output.status == NodeStatus.SUCCESS
        result_df = output.data
        
        assert len(result_df) == 3  # Bob(30), David(35), Charlie(28)
        assert set(result_df["name"]) == {"Bob", "Charlie", "David"}
    
    def test_execute_equality_condition(self):
        """测试等值条件"""
        df = create_test_dataframe()
        node = FilterNode(node_id="test", condition="city == 'Beijing'")
        
        inputs = {"data": NodeInput(data=df)}
        result = node.run(inputs=inputs)
        
        result_df = result["data"].data
        assert len(result_df) == 2  # Alice, Charlie
        assert all(result_df["city"] == "Beijing")
    
    def test_execute_multiple_conditions(self):
        """测试多条件过滤"""
        df = create_test_dataframe()
        node = FilterNode(
            node_id="test",
            condition="age > 25 and score >= 90"
        )
        
        inputs = {"data": NodeInput(data=df)}
        result = node.run(inputs=inputs)
        
        result_df = result["data"].data
        assert len(result_df) == 2  # Charlie(28,92), Eve(27,90)
    
    def test_execute_or_condition(self):
        """测试OR条件"""
        df = create_test_dataframe()
        node = FilterNode(
            node_id="test",
            condition="age < 27 or age > 30"
        )
        
        inputs = {"data": NodeInput(data=df)}
        result = node.run(inputs=inputs)
        
        result_df = result["data"].data
        assert len(result_df) == 2  # Alice(25), David(35)
    
    def test_execute_no_matches(self):
        """测试没有匹配的行"""
        df = create_test_dataframe()
        node = FilterNode(node_id="test", condition="age > 100")
        
        inputs = {"data": NodeInput(data=df)}
        result = node.run(inputs=inputs)
        
        result_df = result["data"].data
        assert len(result_df) == 0
        assert list(result_df.columns) == list(df.columns)
    
    def test_execute_all_matches(self):
        """测试所有行都匹配"""
        df = create_test_dataframe()
        node = FilterNode(node_id="test", condition="age > 0")
        
        inputs = {"data": NodeInput(data=df)}
        result = node.run(inputs=inputs)
        
        result_df = result["data"].data
        assert len(result_df) == 5
    
    def test_execute_invalid_condition_raises(self):
        """测试无效条件"""
        df = create_test_dataframe()
        node = FilterNode(node_id="test", condition="nonexistent_column > 10")
        
        inputs = {"data": NodeInput(data=df)}
        result = node.run(inputs=inputs)
        
        output = result["data"]
        assert output.status == NodeStatus.FAILED
        assert "过滤条件无效" in str(output.error)


class TestFilterNodeColumnSelection:
    """测试列选择功能"""
    
    def test_execute_select_columns(self):
        """测试选择指定列"""
        df = create_test_dataframe()
        node = FilterNode(
            node_id="test",
            columns=["name", "score"]
        )
        
        inputs = {"data": NodeInput(data=df)}
        result = node.run(inputs=inputs)
        
        result_df = result["data"].data
        assert list(result_df.columns) == ["name", "score"]
        assert len(result_df) == 5
    
    def test_execute_select_single_column(self):
        """测试选择单列"""
        df = create_test_dataframe()
        node = FilterNode(node_id="test", columns=["name"])
        
        inputs = {"data": NodeInput(data=df)}
        result = node.run(inputs=inputs)
        
        result_df = result["data"].data
        assert list(result_df.columns) == ["name"]
    
    def test_execute_select_nonexistent_column_raises(self):
        """测试选择不存在的列"""
        df = create_test_dataframe()
        node = FilterNode(node_id="test", columns=["name", "nonexistent"])
        
        inputs = {"data": NodeInput(data=df)}
        result = node.run(inputs=inputs)
        
        output = result["data"]
        assert output.status == NodeStatus.FAILED
        assert "列不存在" in str(output.error)


class TestFilterNodeCombined:
    """测试行过滤和列选择组合"""
    
    def test_execute_filter_and_select(self):
        """测试同时过滤行和选择列"""
        df = create_test_dataframe()
        node = FilterNode(
            node_id="test",
            condition="age > 27",
            columns=["name", "age"]
        )
        
        inputs = {"data": NodeInput(data=df)}
        result = node.run(inputs=inputs)
        
        result_df = result["data"].data
        assert len(result_df) == 3  # Bob, Charlie, David
        assert list(result_df.columns) == ["name", "age"]
    
    def test_execute_complex_workflow(self):
        """测试复杂的过滤和选择"""
        df = create_test_dataframe()
        node = FilterNode(
            node_id="test",
            condition="(age > 25 and score >= 90) or city == 'Shanghai'",
            columns=["name", "city", "score"]
        )
        
        inputs = {"data": NodeInput(data=df)}
        result = node.run(inputs=inputs)
        
        result_df = result["data"].data
        # Bob(Shanghai), Charlie(age>25 and score>=90), Eve(Shanghai and age>25 and score>=90)
        assert len(result_df) == 3
        assert list(result_df.columns) == ["name", "city", "score"]


class TestFilterNodeMetadata:
    """测试metadata生成"""
    
    def test_metadata_basic_info(self):
        """测试metadata包含基本信息"""
        df = create_test_dataframe()
        node = FilterNode(node_id="test", condition="age > 27")
        
        inputs = {"data": NodeInput(data=df)}
        result = node.run(inputs=inputs)
        
        metadata = result["data"].metadata
        assert metadata["original_shape"] == (5, 4)
        assert metadata["result_shape"] == (3, 4)
        assert metadata["rows_filtered"] == 2
        assert metadata["condition"] == "age > 27"
    
    def test_metadata_filter_rate(self):
        """测试过滤率计算"""
        df = create_test_dataframe()
        node = FilterNode(node_id="test", condition="age > 27")
        
        inputs = {"data": NodeInput(data=df)}
        result = node.run(inputs=inputs)
        
        metadata = result["data"].metadata
        assert metadata["filter_rate"] == 0.4  # 2/5 = 40%


class TestRowFilterNode:
    """测试RowFilterNode便捷类"""
    
    def test_row_filter_node(self):
        """测试RowFilterNode"""
        df = create_test_dataframe()
        node = RowFilterNode(
            node_id="test",
            condition="age > 27"
        )
        
        assert node.condition == "age > 27"
        assert node.columns is None
        
        inputs = {"data": NodeInput(data=df)}
        result = node.run(inputs=inputs)
        
        result_df = result["data"].data
        assert len(result_df) == 3
        assert len(result_df.columns) == 4  # 所有列都保留
    
    def test_row_filter_node_without_condition_raises(self):
        """测试RowFilterNode必须有condition"""
        with pytest.raises(ValueError, match="必须指定condition"):
            RowFilterNode(node_id="test")


class TestColumnSelectNode:
    """测试ColumnSelectNode便捷类"""
    
    def test_column_select_node(self):
        """测试ColumnSelectNode"""
        df = create_test_dataframe()
        node = ColumnSelectNode(
            node_id="test",
            columns=["name", "score"]
        )
        
        assert node.condition is None
        assert node.columns == ["name", "score"]
        
        inputs = {"data": NodeInput(data=df)}
        result = node.run(inputs=inputs)
        
        result_df = result["data"].data
        assert len(result_df) == 5  # 所有行都保留
        assert list(result_df.columns) == ["name", "score"]
    
    def test_column_select_node_without_columns_raises(self):
        """测试ColumnSelectNode必须有columns"""
        with pytest.raises(ValueError, match="必须指定columns"):
            ColumnSelectNode(node_id="test")


class TestFilterNodeEdgeCases:
    """测试边界情况"""
    
    def test_execute_with_empty_dataframe(self):
        """测试空DataFrame"""
        df = pd.DataFrame(columns=["name", "age"])
        node = FilterNode(node_id="test", condition="age > 25")
        
        inputs = {"data": NodeInput(data=df)}
        result = node.run(inputs=inputs)
        
        result_df = result["data"].data
        assert len(result_df) == 0
        assert list(result_df.columns) == ["name", "age"]
    
    def test_execute_with_non_dataframe_raises(self):
        """测试非DataFrame输入"""
        node = FilterNode(node_id="test", condition="age > 25")
        
        inputs = {"data": NodeInput(data=[1, 2, 3])}  # 列表而非DataFrame
        result = node.run(inputs=inputs)
        
        output = result["data"]
        assert output.status == NodeStatus.FAILED
        assert "期望输入为DataFrame" in str(output.error)
    
    def test_get_filter_info(self):
        """测试获取过滤器信息"""
        node = FilterNode(
            node_id="test",
            condition="age > 25",
            columns=["name", "age"]
        )
        
        info = node.get_filter_info()
        assert info["condition"] == "age > 25"
        assert info["columns"] == ["name", "age"]
        assert info["has_row_filter"] is True
        assert info["has_column_select"] is True


class TestFilterNodeIntegration:
    """集成测试"""
    
    def test_multiple_filters_in_sequence(self):
        """测试串联多个过滤器（模拟工作流）"""
        df = create_test_dataframe()
        
        # 第一个过滤器：过滤年龄
        filter1 = FilterNode(node_id="filter1", condition="age > 25")
        inputs1 = {"data": NodeInput(data=df)}
        result1 = filter1.run(inputs=inputs1)
        df1 = result1["data"].data
        assert len(df1) == 4
        
        # 第二个过滤器：选择列
        filter2 = FilterNode(node_id="filter2", columns=["name", "score"])
        inputs2 = {"data": NodeInput(data=df1)}
        result2 = filter2.run(inputs=inputs2)
        df2 = result2["data"].data
        
        assert len(df2) == 4
        assert list(df2.columns) == ["name", "score"]
    
    def test_reset_and_reexecute(self):
        """测试重置后重新执行"""
        df = create_test_dataframe()
        node = FilterNode(node_id="test", condition="age > 27")
        
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

