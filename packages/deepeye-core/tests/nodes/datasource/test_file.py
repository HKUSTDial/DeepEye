"""测试FileDataSourceNode节点"""

import pytest
import pandas as pd
from pathlib import Path
from pandas.testing import assert_frame_equal

from deepeye.nodes.datasource import (
    FileDataSourceNode,
    CSVDataSourceNode,
    JSONDataSourceNode,
)
from deepeye.nodes.io import NodeStatus


# 测试数据目录
TEST_DATA_DIR = Path(__file__).parent.parent.parent / "test_data"
CSV_FILE = TEST_DATA_DIR / "sample.csv"
JSON_FILE = TEST_DATA_DIR / "sample.json"


class TestFileDataSourceNode:
    """测试FileDataSourceNode基本功能"""
    
    def test_init_with_csv_path(self):
        """测试使用CSV文件路径初始化"""
        node = FileDataSourceNode(node_id="test", config={"file_path": str(CSV_FILE)})
        assert node.node_id == "test"
        assert node.node_type == "FileDataSource"
        assert node.config.file_path == str(CSV_FILE)
    
    def test_init_without_path_raises(self):
        """测试缺少文件路径时抛出错误"""
        with pytest.raises(ValueError, match="file_path 参数不能为空"):
            FileDataSourceNode(node_id="test", config={"file_path": None})
    
    def test_init_with_url(self):
        """测试使用URL初始化"""
        url = "https://example.com/data.csv"
        node = FileDataSourceNode(node_id="test", config={"file_path": url})
        assert node.config.file_path == url
        assert node._is_url(url)
    
    def test_init_with_url_not_allowed_raises(self):
        """测试不允许URL时抛出错误"""
        with pytest.raises(ValueError, match="不允许从URL读取"):
            FileDataSourceNode(
                node_id="test",
                config={
                    "file_path": "https://example.com/data.csv",
                    "allow_remote": False
                }
            )
    
    def test_init_with_negative_nrows_raises(self):
        """测试负数nrows抛出错误"""
        with pytest.raises(ValueError, match="nrows 必须为正数"):
            FileDataSourceNode(
                node_id="test",
                config={
                    "file_path": str(CSV_FILE),
                    "nrows": -10
                }
            )
    
    def test_init_with_nrows_exceeds_max_raises(self):
        """测试nrows超过限制抛出错误"""
        with pytest.raises(ValueError, match="超过最大限制"):
            FileDataSourceNode(
                node_id="test",
                config={
                    "file_path": str(CSV_FILE),
                    "nrows": 200000,
                    "max_rows": 100000
                }
            )
    
    def test_detect_file_type_csv(self):
        """测试自动检测CSV类型"""
        node = FileDataSourceNode(node_id="test", config={"file_path": "data.csv"})
        assert node._detect_file_type("data.csv") == "csv"
        assert node._detect_file_type("DATA.CSV") == "csv"
    
    def test_detect_file_type_json(self):
        """测试自动检测JSON类型"""
        node = FileDataSourceNode(node_id="test", config={"file_path": "data.json"})
        assert node._detect_file_type("data.json") == "json"
    
    def test_detect_file_type_unsupported_raises(self):
        """测试不支持的文件类型抛出错误"""
        node = FileDataSourceNode(node_id="test", config={"file_path": "data.txt"})
        with pytest.raises(ValueError, match="无法识别文件类型"):
            node._detect_file_type("data.txt")


class TestFileDataSourceCSV:
    """测试CSV文件读取"""
    
    def test_execute_read_csv(self):
        """测试读取CSV文件"""
        node = FileDataSourceNode(
            node_id="test",
            config={"file_path": str(CSV_FILE)}
        )
        
        result = node.run(inputs={})
        output = result["data"]
        
        assert output.status == NodeStatus.SUCCESS
        assert isinstance(output.data, dict)
        assert "dataframe" in output.data
        df = output.data["dataframe"]
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 5
        assert list(df.columns) == ["name", "age", "city", "score"]
        assert df.loc[0, "name"] == "Alice"
        assert df.loc[0, "age"] == 25
    
    def test_execute_read_csv_with_nrows(self):
        """测试读取CSV文件（限制行数）"""
        node = FileDataSourceNode(
            node_id="test",
            config={
                "file_path": str(CSV_FILE),
                "nrows": 3
            }
        )
        
        result = node.run(inputs={})
        df = result["data"].data["dataframe"]
        
        assert len(df) == 3
        assert df.loc[2, "name"] == "Charlie"
    
    def test_execute_read_csv_with_usecols(self):
        """测试读取CSV文件（限制列）"""
        node = FileDataSourceNode(
            node_id="test",
            config={
                "file_path": str(CSV_FILE),
                "usecols": ["name", "score"]
            }
        )
        
        result = node.run(inputs={})
        df = result["data"].data["dataframe"]
        
        assert list(df.columns) == ["name", "score"]
        assert "age" not in df.columns
    
    def test_execute_read_csv_with_custom_delimiter(self):
        """测试读取自定义分隔符的CSV"""
        # 创建临时文件
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write("a;b;c\n1;2;3\n4;5;6\n")
            temp_file = f.name
        
        try:
            node = FileDataSourceNode(
                node_id="test",
                config={
                    "file_path": temp_file,
                    "delimiter": ";"
                }
            )
            
            result = node.run(inputs={})
            df = result["data"].data["dataframe"]
            
            assert len(df) == 2
            assert list(df.columns) == ["a", "b", "c"]
        finally:
            Path(temp_file).unlink()
    
    def test_execute_read_csv_file_not_found(self):
        """测试文件不存在时抛出错误"""
        node = FileDataSourceNode(
            node_id="test",
            config={
                "file_path": "nonexistent.csv"
            }
        )
        
        result = node.run(inputs={})
        output = result["data"]
        
        assert output.status == NodeStatus.FAILED
        assert "文件不存在" in str(output.error)
    
    def test_metadata_for_csv(self):
        """测试CSV文件的metadata"""
        node = FileDataSourceNode(
            node_id="test",
            config={
                "file_path": str(CSV_FILE)
            }
        )
        
        result = node.run(inputs={})
        metadata = result["data"].metadata
        
        assert metadata["source_type"] == "FileDataSource"
        assert metadata["rows"] == 5
        assert "source_info" in metadata
        assert metadata["source_info"]["file_path"] == str(CSV_FILE)
        assert metadata["source_info"]["is_remote"] == False


class TestFileDataSourceJSON:
    """测试JSON文件读取"""
    
    def test_execute_read_json(self):
        """测试读取JSON文件"""
        node = FileDataSourceNode(
            node_id="test",
            config={
                "file_path": str(JSON_FILE),
                "file_type": "json"
            }
        )
        
        result = node.run(inputs={})
        output = result["data"]
        
        assert output.status == NodeStatus.SUCCESS
        assert isinstance(output.data, dict)
        assert "dataframe" in output.data
        df = output.data["dataframe"]
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 3
        assert list(df.columns) == ["product", "price", "quantity"]
        assert df.loc[0, "product"] == "iPhone"
    
    def test_execute_read_json_auto_detect(self):
        """测试自动检测JSON文件类型"""
        node = FileDataSourceNode(
            node_id="test",
            config={"file_path": str(JSON_FILE)}  # 自动检测
        )
        
        result = node.run(inputs={})
        df = result["data"].data["dataframe"]
        
        assert len(df) == 3
    
    def test_execute_read_json_with_nrows(self):
        """测试读取JSON文件（限制行数）"""
        node = FileDataSourceNode(
            node_id="test",
            config={
                "file_path": str(JSON_FILE),
                "nrows": 2
            }
        )
        
        result = node.run(inputs={})
        df = result["data"].data["dataframe"]
        
        assert len(df) == 2


class TestCSVDataSource:
    """测试CSVDataSource便捷类"""
    
    def test_csv_datasource(self):
        """测试CSVDataSource"""
        node = CSVDataSourceNode(
            node_id="test",
            config={"file_path": str(CSV_FILE)}
        )
        
        assert node.config.file_type == "csv"
        
        result = node.run(inputs={})
        df = result["data"].data["dataframe"]
        
        assert len(df) == 5
        assert "name" in df.columns


class TestJSONDataSource:
    """测试JSONDataSource便捷类"""
    
    def test_json_datasource(self):
        """测试JSONDataSource"""
        node = JSONDataSourceNode(
            node_id="test",
            config={"file_path": str(JSON_FILE)}
        )
        
        assert node.config.file_type == "json"
        
        result = node.run(inputs={})
        df = result["data"].data["dataframe"]
        
        assert len(df) == 3
        assert "product" in df.columns


class TestFileDataSourceIntegration:
    """集成测试"""
    
    def test_csv_to_json_workflow(self):
        """测试CSV读取后的数据处理（模拟工作流）"""
        # 读取CSV
        csv_node = FileDataSourceNode(
            node_id="csv_source",
            config={"file_path": str(CSV_FILE)}
        )
        
        result = csv_node.run(inputs={})
        df = result["data"].data["dataframe"]
        
        # 模拟下游处理：过滤数据
        filtered = df[df["age"] > 27]
        assert len(filtered) == 3
        
        # 模拟下游处理：计算统计
        avg_score = df["score"].mean()
        assert avg_score == 90.4
    
    def test_file_source_reset_and_reexecute(self):
        """测试重置后重新执行"""
        node = FileDataSourceNode(
            node_id="test",
            config={"file_path": str(CSV_FILE)}
        )
        
        # 第一次执行
        result1 = node.run(inputs={})
        df1 = result1["data"].data["dataframe"]
        
        # 重置
        node.reset()
        
        # 第二次执行
        result2 = node.run(inputs={})
        df2 = result2["data"].data["dataframe"]
        
        # 两次结果应该相同
        assert_frame_equal(df1, df2)

