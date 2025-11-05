"""DeepEye 异常定义"""


class DeepEyeError(Exception):
    """DeepEye 基础异常类"""
    pass


class NodeError(DeepEyeError):
    """节点相关异常"""
    pass


class NodeExecutionError(NodeError):
    """节点执行失败异常"""
    pass


class NodeValidationError(NodeError):
    """节点验证失败异常"""
    pass


class NodeNotFoundError(NodeError):
    """节点不存在异常"""
    pass


class WorkflowError(DeepEyeError):
    """工作流相关异常"""
    pass


class WorkflowValidationError(WorkflowError):
    """工作流验证失败异常"""
    pass


class WorkflowExecutionError(WorkflowError):
    """工作流执行失败异常"""
    pass


class CyclicDependencyError(WorkflowError):
    """工作流存在循环依赖异常"""
    pass


class AgentError(DeepEyeError):
    """Agent 相关异常"""
    pass


class AgentPlanningError(AgentError):
    """Agent 规划失败异常"""
    pass


class LLMError(DeepEyeError):
    """LLM 相关异常"""
    pass


class LLMAPIError(LLMError):
    """LLM API 调用失败异常"""
    pass


class LLMTimeoutError(LLMError):
    """LLM 调用超时异常"""
    pass


class StorageError(DeepEyeError):
    """存储相关异常"""
    pass


class PluginError(DeepEyeError):
    """插件相关异常"""
    pass


class PluginLoadError(PluginError):
    """插件加载失败异常"""
    pass


class ConfigurationError(DeepEyeError):
    """配置错误异常"""
    pass


class ValidationError(DeepEyeError):
    """数据验证错误异常"""
    pass

