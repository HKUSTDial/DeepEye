"""全局配置管理器测试"""

import pytest
from deepeye.config import GlobalConfig, get_global_config


class TestGlobalConfigSingleton:
    """测试单例模式"""
    
    def test_singleton(self):
        """测试单例模式 - 多次调用返回同一实例"""
        config1 = GlobalConfig()
        config2 = GlobalConfig()
        config3 = get_global_config()
        
        assert config1 is config2
        assert config2 is config3
    
    def test_singleton_across_imports(self):
        """测试跨导入的单例"""
        from deepeye.config import get_global_config as get_config_1
        from deepeye.config.global_config import get_global_config as get_config_2
        
        config1 = get_config_1()
        config2 = get_config_2()
        
        assert config1 is config2


class TestGlobalConfigBasicOperations:
    """测试基本操作"""
    
    @pytest.fixture(autouse=True)
    def setup_teardown(self):
        """每个测试前后清理配置"""
        config = get_global_config()
        config.clear_all()
        yield
        config.clear_all()
    
    def test_set_and_get_config(self):
        """测试设置和获取配置"""
        config = get_global_config()
        
        test_config = {
            "file_path": "/data/test.csv",
            "encoding": "utf-8"
        }
        
        config.set_node_config("FileDataSource", test_config)
        retrieved = config.get_node_config("FileDataSource")
        
        assert retrieved == test_config
    
    def test_get_nonexistent_config(self):
        """测试获取不存在的配置"""
        config = get_global_config()
        
        result = config.get_node_config("NonExistent")
        assert result is None
        
        result_with_default = config.get_node_config("NonExistent", default={"key": "value"})
        assert result_with_default == {"key": "value"}
    
    def test_has_node_config(self):
        """测试检查配置是否存在"""
        config = get_global_config()
        
        assert not config.has_node_config("FileDataSource")
        
        config.set_node_config("FileDataSource", {"file_path": "/data/test.csv"})
        assert config.has_node_config("FileDataSource")
    
    def test_clear_node_config(self):
        """测试清除单个节点配置"""
        config = get_global_config()
        
        config.set_node_config("FileDataSource", {"file_path": "/data/test.csv"})
        config.set_node_config("DatabaseDataSource", {"connection_string": "sqlite:///db"})
        
        assert config.has_node_config("FileDataSource")
        assert config.has_node_config("DatabaseDataSource")
        
        config.clear_node_config("FileDataSource")
        
        assert not config.has_node_config("FileDataSource")
        assert config.has_node_config("DatabaseDataSource")
    
    def test_clear_all(self):
        """测试清除所有配置"""
        config = get_global_config()
        
        config.set_node_config("FileDataSource", {"file_path": "/data/test.csv"})
        config.set_node_config("DatabaseDataSource", {"connection_string": "sqlite:///db"})
        
        assert len(config.list_configured_nodes()) == 2
        
        config.clear_all()
        
        assert len(config.list_configured_nodes()) == 0


class TestGlobalConfigMerge:
    """测试配置合并"""
    
    @pytest.fixture(autouse=True)
    def setup_teardown(self):
        """每个测试前后清理配置"""
        config = get_global_config()
        config.clear_all()
        yield
        config.clear_all()
    
    def test_set_config_with_merge_false(self):
        """测试完全覆盖模式"""
        config = get_global_config()
        
        config.set_node_config("FileDataSource", {
            "file_path": "/data/test.csv",
            "encoding": "utf-8"
        })
        
        config.set_node_config("FileDataSource", {
            "file_path": "/data/new.csv"
        }, merge=False)
        
        result = config.get_node_config("FileDataSource")
        assert result == {"file_path": "/data/new.csv"}
        assert "encoding" not in result
    
    def test_set_config_with_merge_true(self):
        """测试合并模式"""
        config = get_global_config()
        
        config.set_node_config("FileDataSource", {
            "file_path": "/data/test.csv",
            "encoding": "utf-8"
        })
        
        config.set_node_config("FileDataSource", {
            "delimiter": ","
        }, merge=True)
        
        result = config.get_node_config("FileDataSource")
        assert result == {
            "file_path": "/data/test.csv",
            "encoding": "utf-8",
            "delimiter": ","
        }
    
    def test_merge_with_config_no_global(self):
        """测试合并配置 - 没有全局配置"""
        config = get_global_config()
        
        user_config = {"file_path": "/data/test.csv"}
        merged = config.merge_with_config("FileDataSource", user_config)
        
        assert merged == user_config
    
    def test_merge_with_config_no_user(self):
        """测试合并配置 - 没有用户配置"""
        config = get_global_config()
        
        global_config = {"file_path": "/data/test.csv", "encoding": "utf-8"}
        config.set_node_config("FileDataSource", global_config)
        
        merged = config.merge_with_config("FileDataSource", None)
        
        assert merged == global_config
    
    def test_merge_with_config_both(self):
        """测试合并配置 - 用户配置覆盖全局配置"""
        config = get_global_config()
        
        config.set_node_config("FileDataSource", {
            "file_path": "/data/test.csv",
            "encoding": "utf-8",
            "delimiter": ","
        })
        
        user_config = {
            "encoding": "gbk",  # 覆盖
            "nrows": 1000       # 新增
        }
        
        merged = config.merge_with_config("FileDataSource", user_config)
        
        assert merged == {
            "file_path": "/data/test.csv",  # 来自全局
            "encoding": "gbk",              # 用户覆盖
            "delimiter": ",",               # 来自全局
            "nrows": 1000                   # 用户新增
        }


class TestGlobalConfigUtilities:
    """测试工具方法"""
    
    @pytest.fixture(autouse=True)
    def setup_teardown(self):
        """每个测试前后清理配置"""
        config = get_global_config()
        config.clear_all()
        yield
        config.clear_all()
    
    def test_list_configured_nodes(self):
        """测试列出已配置的节点"""
        config = get_global_config()
        
        config.set_node_config("FileDataSource", {"file_path": "/data/test.csv"})
        config.set_node_config("DatabaseDataSource", {"connection_string": "sqlite:///db"})
        config.set_node_config("DataCoderNode", {"max_iterations": 5})
        
        configured = config.list_configured_nodes()
        
        assert len(configured) == 3
        assert "FileDataSource" in configured
        assert "DatabaseDataSource" in configured
        assert "DataCoderNode" in configured
    
    def test_get_all_configs(self):
        """测试获取所有配置"""
        config = get_global_config()
        
        config.set_node_config("FileDataSource", {"file_path": "/data/test.csv"})
        config.set_node_config("DatabaseDataSource", {"connection_string": "sqlite:///db"})
        
        all_configs = config.get_all_configs()
        
        assert len(all_configs) == 2
        assert all_configs["FileDataSource"] == {"file_path": "/data/test.csv"}
        assert all_configs["DatabaseDataSource"] == {"connection_string": "sqlite:///db"}
    
    def test_deep_copy_isolation(self):
        """测试深拷贝隔离 - 修改返回的配置不影响原始配置"""
        config = get_global_config()
        
        original = {
            "file_path": "/data/test.csv",
            "options": {"encoding": "utf-8"}
        }
        config.set_node_config("FileDataSource", original)
        
        # 获取配置并修改
        retrieved = config.get_node_config("FileDataSource")
        retrieved["file_path"] = "/data/modified.csv"
        retrieved["options"]["encoding"] = "gbk"
        
        # 原始配置应该不受影响
        check = config.get_node_config("FileDataSource")
        assert check["file_path"] == "/data/test.csv"
        assert check["options"]["encoding"] == "utf-8"
    
    def test_repr(self):
        """测试字符串表示"""
        config = get_global_config()
        
        config.set_node_config("FileDataSource", {"file_path": "/data/test.csv"})
        config.set_node_config("DatabaseDataSource", {"connection_string": "sqlite:///db"})
        
        repr_str = repr(config)
        
        assert "GlobalConfig" in repr_str
        assert "2" in repr_str  # 2个配置的节点


class TestGlobalConfigThreadSafety:
    """测试线程安全"""
    
    @pytest.fixture(autouse=True)
    def setup_teardown(self):
        """每个测试前后清理配置"""
        config = get_global_config()
        config.clear_all()
        yield
        config.clear_all()
    
    def test_concurrent_writes(self):
        """测试并发写入"""
        import threading
        
        config = get_global_config()
        errors = []
        
        def write_config(node_type: str, value: str):
            try:
                for i in range(100):
                    config.set_node_config(node_type, {"value": f"{value}_{i}"})
            except Exception as e:
                errors.append(e)
        
        threads = [
            threading.Thread(target=write_config, args=(f"Node{i}", f"value{i}"))
            for i in range(10)
        ]
        
        for t in threads:
            t.start()
        
        for t in threads:
            t.join()
        
        # 不应该有错误
        assert len(errors) == 0
        
        # 应该有10个配置的节点
        assert len(config.list_configured_nodes()) == 10

