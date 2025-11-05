"""LLM相关异常定义"""

from deepeye.exceptions import DeepEyeError


class LLMError(DeepEyeError):
    """LLM错误基类"""
    pass


class LLMAPIError(LLMError):
    """LLM API调用错误"""
    pass


class LLMTimeoutError(LLMError):
    """LLM调用超时"""
    pass


class LLMRateLimitError(LLMError):
    """LLM API速率限制"""
    pass


class LLMAuthenticationError(LLMError):
    """LLM认证失败"""
    pass

