"""节点与全局配置集成测试"""

import pytest
import pandas as pd
from deepeye.config import get_global_config
from deepeye.nodes.datasource import FileDataSourceNode, MemoryDataSourceNode


class TestNodeGlobalConfigIntegration:
    """测试节点使用全局配置"""
    
    @pytest.fixture(autouse=True)
    def setup_teardown(self):
        """每个测试前后清理配置"""
        config = get_global_config()
        config.clear_all()
        yield
        config.clear_all()
    
    def test_node_uses_global_config(self, tmp_path):
        """测试节点自动使用全局配置"""
        # 创建测试CSV文件
        csv_file = tmp_path / "test.csv"
        df = pd.DataFrame({"A": [1, 2, 3], "B": [4, 5, 6]})
        df.to_csv(csv_file, index=False)
        
        # 设置全局配置
        config = get_global_config()
        config.set_node_config("FileDataSource", {
            "file_path": str(csv_file),
            "file_type": "csv"
        })
        
        # 创建节点时不传递config - 应该自动使用全局配置
        node = FileDataSourceNode(node_id="test")
        
        # 验证配置被正确加载
        assert node.config.file_path == str(csv_file)
        
        # 节点应该能正常执行
        result = node.run({})
        assert "data" in result
        # CSV节点返回字典 {"dataframe": df}
        assert isinstance(result["data"].data, dict)
        assert "dataframe" in result["data"].data
        output_df = result["data"].data["dataframe"]
        assert isinstance(output_df, pd.DataFrame)
        assert len(output_df) == 3
    
    def test_user_config_overrides_global_config(self, tmp_path):
        """测试用户配置覆盖全局配置"""
        # 创建两个CSV文件
        global_csv = tmp_path / "global.csv"
        user_csv = tmp_path / "user.csv"
        
        pd.DataFrame({"A": [1, 2]}).to_csv(global_csv, index=False)
        pd.DataFrame({"B": [3, 4, 5]}).to_csv(user_csv, index=False)
        
        # 设置全局配置
        config = get_global_config()
        config.set_node_config("FileDataSource", {
            "file_path": str(global_csv),
            "file_type": "csv"
        })
        
        # 创建节点时传递config - 应该覆盖全局配置
        node = FileDataSourceNode(
            node_id="test",
            config={"file_path": str(user_csv), "file_type": "csv"}
        )
        
        # 验证使用的是用户配置
        assert node.config.file_path == str(user_csv)
        
        # 节点执行应该使用用户文件
        result = node.run({})
        output_df = result["data"].data["dataframe"]
        assert isinstance(output_df, pd.DataFrame)
        assert len(output_df) == 3  # user_csv 有3行
        assert "B" in output_df.columns  # user_csv 有列B
    
    def test_partial_config_merge(self, tmp_path):
        """测试部分配置合并"""
        # 创建测试CSV文件
        csv_file = tmp_path / "test.csv"
        df = pd.DataFrame({"A": [1, 2, 3], "B": [4, 5, 6]})
        df.to_csv(csv_file, index=False)
        
        # 设置全局配置（完整配置）
        config = get_global_config()
        config.set_node_config("FileDataSource", {
            "file_path": str(csv_file),
            "file_type": "csv",
            "encoding": "utf-8",
            "delimiter": ","
        })
        
        # 用户只覆盖部分参数
        node = FileDataSourceNode(
            node_id="test",
            config={
                "encoding": "gbk",  # 覆盖
                "nrows": 2          # 新增
            }
        )
        
        # 验证配置合并正确
        assert node.config.file_path == str(csv_file)  # 来自全局
        assert node.config.encoding == "gbk"  # 用户覆盖
        assert node.config.delimiter == ","   # 来自全局
        assert node.config.nrows == 2         # 用户新增
    
    def test_no_global_config_uses_defaults(self):
        """测试没有全局配置时使用节点默认值"""
        # 不设置全局配置
        # MemoryDataSourceNode 允许空配置（数据通过input传入）
        node = MemoryDataSourceNode(node_id="test")
        
        # 应该使用默认配置
        assert node.config is not None
    
    def test_multiple_nodes_with_different_configs(self, tmp_path):
        """测试多个节点使用不同的全局配置"""
        # 创建测试文件
        csv_file = tmp_path / "test.csv"
        pd.DataFrame({"A": [1, 2, 3]}).to_csv(csv_file, index=False)
        
        # 为不同节点类型设置全局配置
        config = get_global_config()
        config.set_node_config("FileDataSource", {
            "file_path": str(csv_file),
            "file_type": "csv"
        })
        
        # 创建不同类型的节点
        file_node = FileDataSourceNode(node_id="file")
        
        # 验证配置正确
        assert file_node.config.file_path == str(csv_file)
        assert file_node.config.file_type == "csv"
    
    def test_global_config_isolation_between_instances(self, tmp_path):
        """测试全局配置在节点实例之间的隔离"""
        # 创建测试文件
        csv_file = tmp_path / "test.csv"
        pd.DataFrame({"A": [1, 2, 3]}).to_csv(csv_file, index=False)
        
        # 设置全局配置
        config = get_global_config()
        config.set_node_config("FileDataSource", {
            "file_path": str(csv_file),
            "file_type": "csv"
        })
        
        # 创建第一个节点
        node1 = FileDataSourceNode(node_id="node1")
        
        # 修改节点1的配置（运行时修改）
        node1.config.encoding = "gbk"
        
        # 创建第二个节点
        node2 = FileDataSourceNode(node_id="node2")
        
        # 节点2应该不受节点1的影响
        assert node2.config.encoding == "utf-8"  # 默认值
        
        # 全局配置也不应该被影响
        global_cfg = config.get_node_config("FileDataSource")
        assert "encoding" not in global_cfg or global_cfg.get("encoding") != "gbk"


class TestGlobalConfigWithAgentRegistration:
    """测试在 Agent 中使用全局配置注册节点"""
    
    @pytest.fixture(autouse=True)
    def setup_teardown(self):
        """每个测试前后清理配置"""
        config = get_global_config()
        config.clear_all()
        yield
        config.clear_all()
    
    def test_register_node_without_required_config_fails(self):
        """测试没有全局配置时注册需要配置的节点会失败"""
        from deepeye.nodes.registry import NodeRegistry
        
        registry = NodeRegistry()
        
        # 注册节点类（不会失败，因为只是注册类）
        registry.register(FileDataSourceNode)
        
        # 创建节点实例时会失败（没有file_path）
        with pytest.raises(Exception):  # 会抛出配置错误
            registry.create_node("FileDataSource", validate_on_init=True)
    
    def test_register_node_with_global_config_succeeds(self, tmp_path):
        """测试有全局配置时注册节点成功"""
        from deepeye.nodes.registry import NodeRegistry
        
        # 创建测试文件
        csv_file = tmp_path / "test.csv"
        pd.DataFrame({"A": [1, 2, 3]}).to_csv(csv_file, index=False)
        
        # 设置全局配置
        config = get_global_config()
        config.set_node_config("FileDataSource", {
            "file_path": str(csv_file),
            "file_type": "csv"
        })
        
        # 注册并创建节点（使用新的registry实例，避免冲突）
        registry = NodeRegistry()
        # 清除可能存在的注册
        if registry.is_registered("FileDataSource"):
            registry.unregister("FileDataSource")
        
        registry.register(FileDataSourceNode)
        node = registry.create_node("FileDataSource")
        
        # 节点应该能正常工作
        assert node.config.file_path == str(csv_file)
        result = node.run({})
        assert "data" in result


class TestGlobalConfigErrorHandling:
    """测试全局配置的错误处理"""
    
    @pytest.fixture(autouse=True)
    def setup_teardown(self):
        """每个测试前后清理配置"""
        config = get_global_config()
        config.clear_all()
        yield
        config.clear_all()
    
    def test_invalid_config_still_raises_error(self):
        """测试无效的配置仍然会抛出错误"""
        from deepeye.nodes.io import NodeStatus
        
        # 设置无效的全局配置
        config = get_global_config()
        config.set_node_config("FileDataSource", {
            "file_path": "/nonexistent/file.csv",
            "file_type": "csv"
        })
        
        # FileDataSourceNode 允许创建（延迟验证）
        node = FileDataSourceNode(node_id="test")
        
        # 执行会返回失败状态（而不是抛出异常）
        result = node.run({})
        assert "data" in result
        assert result["data"].status == NodeStatus.FAILED
        assert "file" in result["data"].error.lower() or "not" in result["data"].error.lower()
    
    def test_empty_global_config_with_required_field(self):
        """测试空全局配置但节点有必需字段"""
        # 不设置全局配置
        # FileDataSource 需要 file_path
        
        # 创建节点应该失败（缺少必需字段）
        with pytest.raises(Exception):
            FileDataSourceNode(node_id="test", validate_on_init=True)


class TestGlobalConfigDocumentation:
    """测试全局配置的文档示例"""
    
    @pytest.fixture(autouse=True)
    def setup_teardown(self):
        """每个测试前后清理配置"""
        config = get_global_config()
        config.clear_all()
        yield
        config.clear_all()
    
    def test_basic_usage_example(self, tmp_path):
        """测试基本使用示例"""
        # 创建测试文件
        csv_file = tmp_path / "sales.csv"
        pd.DataFrame({"product": ["A", "B"], "sales": [100, 200]}).to_csv(csv_file, index=False)
        
        # Example from documentation
        from deepeye.config import get_global_config
        
        # 设置全局配置
        config = get_global_config()
        config.set_node_config("FileDataSource", {
            "file_path": str(csv_file),
            "file_type": "csv",
            "encoding": "utf-8"
        })
        
        # 使用全局配置创建节点（无需传递 config）
        node1 = FileDataSourceNode(node_id="sales")
        assert node1.config.file_path == str(csv_file)
        
        # 显式 config 会覆盖全局配置
        node2 = FileDataSourceNode(
            node_id="custom",
            config={"file_path": str(csv_file), "file_type": "csv", "encoding": "gbk"}
        )
        assert node2.config.encoding == "gbk"
        
        # 部分覆盖
        node3 = FileDataSourceNode(
            node_id="partial",
            config={"encoding": "latin1"}
        )
        assert node3.config.file_path == str(csv_file)  # 来自全局
        assert node3.config.encoding == "latin1"  # 用户覆盖

