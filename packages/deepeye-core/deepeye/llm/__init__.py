"""DeepEye LLM模块

极简的LLM调用接口，基于OpenAI库，支持所有OpenAI兼容的API

Example:
    >>> from deepeye.llm import LLMClient
    >>> 
    >>> # OpenAI
    >>> client = LLMClient(
    ...     api_key="sk-...",
    ...     base_url="https://api.openai.com/v1"
    ... )
    >>> response = client.chat("Hello", model="gpt-4")
    >>> 
    >>> # 通义千问
    >>> client = LLMClient(
    ...     api_key="sk-...",
    ...     base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
    ... )
    >>> response = client.chat("你好", model="qwen-turbo")
"""

from deepeye.llm.client import LLMClient, Message, LLMResponse
from deepeye.llm.exceptions import (
    LLMError,
    LLMAPIError,
    LLMTimeoutError,
    LLMRateLimitError,
    LLMAuthenticationError,
)

__all__ = [
    # 客户端
    "LLMClient",
    "Message",
    "LLMResponse",
    
    # 异常
    "LLMError",
    "LLMAPIError",
    "LLMTimeoutError",
    "LLMRateLimitError",
    "LLMAuthenticationError",
]

