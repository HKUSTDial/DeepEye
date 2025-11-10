"""全局配置管理器

提供单例模式的全局配置管理，用于存储节点的默认配置。
节点在初始化时可以从全局配置中读取配置，避免每次都手动传递配置参数。

注意：
    GlobalConfig 是**可选的**默认配置提供者，主要用于：
    1. 为节点提供默认配置（如数据库连接字符串、API密钥等）
    2. 在 Agent 编排场景中预先配置节点
    
    节点配置的优先级（从高到低）：
    1. 运行时配置（通过 update_config() 或 execute 时的 config 参数）
    2. 初始化时的 config 参数（显式传递）
    3. 全局配置（GlobalConfig）- 可选
    4. 节点的默认值
    
    重要：
    - 节点不再强制要求 GlobalConfig，可以在运行时动态配置
    - 配置验证已延迟到 execute 时，允许先创建节点后配置
    - 使用 update_config() 方法可以在运行时动态更新配置
"""

from typing import Dict, Any, Optional, Type
import copy
from threading import Lock


class GlobalConfig:
    """全局配置管理器（单例模式）
    
    用于管理节点类型的默认配置。节点在初始化时会先从全局配置中查找，
    如果找不到或参数不完整，再从 init 方法的 config 参数读取。
    
    注意：
        GlobalConfig 是**可选的**，主要用于提供默认配置。节点可以在运行时动态配置，
        不需要依赖 GlobalConfig。
    
    配置优先级（从高到低）：
        1. 运行时配置（update_config() 或 execute 时的 config）
        2. init 方法的 config 参数（显式传递）
        3. 全局配置（GlobalConfig）- 可选
        4. 节点的默认值
    
    特性：
        - 单例模式：整个应用共享同一个配置实例
        - 线程安全：使用锁保护配置读写
        - 深拷贝：返回配置副本，避免意外修改
        - 层级覆盖：支持部分配置覆盖
        - 可选性：节点不强制要求全局配置，可在运行时配置
    
    Example - 使用全局配置（传统方式）:
        >>> from deepeye.config import get_global_config
        >>> 
        >>> # 设置全局配置
        >>> config = get_global_config()
        >>> config.set_node_config("FileDataSource", {
        ...     "encoding": "utf-8"  # 只设置默认编码
        ... })
        >>> config.set_node_config("DatabaseDataSource", {
        ...     "connection_string": "sqlite:///app.db",
        ...     "mode": "introspect"
        ... })
        >>> 
        >>> # 使用全局配置创建节点
        >>> node1 = FileDataSourceNode(
        ...     node_id="sales",
        ...     config={"file_path": "/data/sales.csv"}  # 运行时指定文件路径
        ... )
    
    Example - 运行时配置（推荐方式）:
        >>> # 创建节点时不提供配置
        >>> node = FileDataSourceNode(node_id="file1")
        >>> 
        >>> # 用户上传文件后，动态更新配置
        >>> node.update_config({"file_path": "/uploads/user_file.csv"})
        >>> 
        >>> # 执行节点
        >>> result = node.run(inputs={})
    
    Example - 在 Agent 中使用:
        >>> # 在 Agent 中使用全局配置提供默认值
        >>> from deepeye.agent import PlannerAgent
        >>> from deepeye.config import get_global_config
        >>> 
        >>> # 设置工作环境的全局配置（可选）
        >>> config = get_global_config()
        >>> config.set_node_config("DatabaseDataSource", {
        ...     "connection_string": "sqlite:///workspace/app.db"
        ... })
        >>> 
        >>> # 创建 Agent 并注册节点
        >>> agent = PlannerAgent(llm_client=client, model="gpt-4")
        >>> agent.register_node(FileDataSourceNode)  # ✓ 成功，即使没有全局配置
        >>> agent.register_node(DatabaseDataSourceNode)  # ✓ 成功
    """
    
    _instance: Optional["GlobalConfig"] = None
    _lock: Lock = Lock()
    
    def __new__(cls) -> "GlobalConfig":
        """实现单例模式"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self) -> None:
        """初始化全局配置管理器"""
        # 避免重复初始化
        if self._initialized:
            return
        
        self._initialized = True
        self._configs: Dict[str, Dict[str, Any]] = {}
        self._write_lock: Lock = Lock()
    
    def set_node_config(
        self,
        node_type: str,
        config: Dict[str, Any],
        merge: bool = False
    ) -> None:
        """设置节点类型的全局配置
        
        Args:
            node_type: 节点类型名称（如 "FileDataSource"）
            config: 配置字典
            merge: 是否与现有配置合并（默认 False，完全覆盖）
        
        Example:
            >>> config = get_global_config()
            >>> 
            >>> # 设置完整配置
            >>> config.set_node_config("FileDataSource", {
            ...     "file_path": "/data/sales.csv",
            ...     "encoding": "utf-8"
            ... })
            >>> 
            >>> # 合并配置（保留已有的参数）
            >>> config.set_node_config("FileDataSource", {
            ...     "delimiter": ","
            ... }, merge=True)
            >>> # 现在配置包含 file_path, encoding, delimiter
        """
        with self._write_lock:
            if merge and node_type in self._configs:
                # 合并配置
                self._configs[node_type].update(config)
            else:
                # 完全覆盖
                self._configs[node_type] = copy.deepcopy(config)
    
    def get_node_config(
        self,
        node_type: str,
        default: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """获取节点类型的全局配置
        
        Args:
            node_type: 节点类型名称
            default: 默认配置（如果不存在）
        
        Returns:
            配置字典的深拷贝（避免意外修改），如果不存在则返回 default
        
        Example:
            >>> config = get_global_config()
            >>> file_config = config.get_node_config("FileDataSource")
            >>> if file_config:
            ...     print(file_config["file_path"])
        """
        with self._write_lock:
            if node_type in self._configs:
                # 返回深拷贝，避免调用者修改原始配置
                return copy.deepcopy(self._configs[node_type])
            return default
    
    def has_node_config(self, node_type: str) -> bool:
        """检查是否存在节点配置
        
        Args:
            node_type: 节点类型名称
        
        Returns:
            是否存在配置
        
        Example:
            >>> config = get_global_config()
            >>> if config.has_node_config("FileDataSource"):
            ...     print("FileDataSource has global config")
        """
        return node_type in self._configs
    
    def clear_node_config(self, node_type: str) -> None:
        """清除节点类型的全局配置
        
        Args:
            node_type: 节点类型名称
        
        Example:
            >>> config = get_global_config()
            >>> config.clear_node_config("FileDataSource")
        """
        with self._write_lock:
            if node_type in self._configs:
                del self._configs[node_type]
    
    def clear_all(self) -> None:
        """清除所有全局配置
        
        Example:
            >>> config = get_global_config()
            >>> config.clear_all()
        """
        with self._write_lock:
            self._configs.clear()
    
    def list_configured_nodes(self) -> list[str]:
        """列出所有已配置的节点类型
        
        Returns:
            节点类型名称列表
        
        Example:
            >>> config = get_global_config()
            >>> configured = config.list_configured_nodes()
            >>> print(f"Configured nodes: {configured}")
        """
        return list(self._configs.keys())
    
    def get_all_configs(self) -> Dict[str, Dict[str, Any]]:
        """获取所有全局配置（调试用）
        
        Returns:
            所有配置的深拷贝
        
        Example:
            >>> config = get_global_config()
            >>> all_configs = config.get_all_configs()
            >>> for node_type, node_config in all_configs.items():
            ...     print(f"{node_type}: {node_config}")
        """
        with self._write_lock:
            return copy.deepcopy(self._configs)
    
    def merge_with_config(
        self,
        node_type: str,
        user_config: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """将用户配置与全局配置合并
        
        优先级：user_config > global_config
        
        Args:
            node_type: 节点类型名称
            user_config: 用户提供的配置
        
        Returns:
            合并后的配置
        
        Note:
            这是一个工具方法，主要在 BaseNode 内部使用
        
        Example:
            >>> config = get_global_config()
            >>> config.set_node_config("FileDataSource", {
            ...     "file_path": "/data/sales.csv",
            ...     "encoding": "utf-8"
            ... })
            >>> 
            >>> # 用户只提供部分配置
            >>> user_config = {"encoding": "gbk"}
            >>> merged = config.merge_with_config("FileDataSource", user_config)
            >>> # merged = {"file_path": "/data/sales.csv", "encoding": "gbk"}
        """
        # 获取全局配置
        global_config = self.get_node_config(node_type, default={})
        
        # 如果用户没有提供配置，直接返回全局配置
        if user_config is None:
            return global_config
        
        # 合并：用户配置覆盖全局配置
        merged = global_config.copy()
        merged.update(user_config)
        return merged
    
    def __repr__(self) -> str:
        """字符串表示"""
        configured = self.list_configured_nodes()
        return f"<GlobalConfig(configured_nodes={len(configured)}: {configured})>"


def get_global_config() -> GlobalConfig:
    """获取全局配置管理器实例（单例）
    
    这是推荐的访问全局配置的方式。
    
    Returns:
        GlobalConfig 单例实例
    
    Example:
        >>> from deepeye.config import get_global_config
        >>> 
        >>> config = get_global_config()
        >>> config.set_node_config("FileDataSource", {
        ...     "file_path": "/data/sales.csv"
        ... })
    """
    return GlobalConfig()

