"""全局配置管理模块

提供全局配置管理功能，支持节点预配置。
"""

from deepeye.config.global_config import GlobalConfig, get_global_config

__all__ = [
    "GlobalConfig",
    "get_global_config",
]

