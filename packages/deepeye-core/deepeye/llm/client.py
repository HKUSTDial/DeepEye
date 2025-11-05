"""LLM客户端 - 极简实现

基于OpenAI库，支持所有OpenAI兼容的API
"""

from typing import List, Optional, Dict, Any
import time

try:
    from openai import OpenAI, OpenAIError, APITimeoutError, RateLimitError
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False

from pydantic import BaseModel

from deepeye.llm.exceptions import (
    LLMAPIError,
    LLMTimeoutError,
    LLMRateLimitError,
    LLMAuthenticationError,
)


class Message(BaseModel):
    """聊天消息
    
    Example:
        >>> msg = Message(role="user", content="Hello")
        >>> msg = Message(role="system", content="You are a helpful assistant")
    """
    role: str  # "system", "user", "assistant"
    content: str


class LLMResponse(BaseModel):
    """LLM响应
    
    包含生成的内容和元信息（token使用、耗时等）
    
    Example:
        >>> response = client.generate(messages)
        >>> print(response.content)
        >>> print(f"使用了 {response.total_tokens} tokens")
        >>> print(f"耗时 {response.response_time:.2f} 秒")
    """
    content: str
    model: str
    
    # Token使用（从API返回中获取）
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    total_tokens: Optional[int] = None
    
    # 元信息
    finish_reason: Optional[str] = None
    response_time: Optional[float] = None


class LLMClient:
    """统一的LLM客户端
    
    基于OpenAI库，支持所有OpenAI兼容的API提供商
    
    Example:
        >>> # OpenAI
        >>> client = LLMClient(
        ...     api_key="sk-...",
        ...     base_url="https://api.openai.com/v1"
        ... )
        >>> response = client.chat("Hello", model="gpt-4")
        
        >>> # 通义千问
        >>> client = LLMClient(
        ...     api_key="sk-...",
        ...     base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
        ... )
        >>> response = client.chat("你好", model="qwen-turbo")
        
        >>> # 本地Ollama
        >>> client = LLMClient(
        ...     api_key="ollama",  # Ollama不需要真实key
        ...     base_url="http://localhost:11434/v1"
        ... )
        >>> response = client.chat("Hello", model="llama2")
    
    常见提供商的base_url:
        - OpenAI:      https://api.openai.com/v1
        - 通义千问:     https://dashscope.aliyuncs.com/compatible-mode/v1
        - DeepSeek:    https://api.deepseek.com/v1
        - Moonshot:    https://api.moonshot.cn/v1
        - 智谱AI:      https://open.bigmodel.cn/api/paas/v4
        - Ollama:      http://localhost:11434/v1
    """
    
    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.openai.com/v1",
        timeout: int = 60,
        max_retries: int = 3,
    ):
        """初始化LLM客户端
        
        Args:
            api_key: API密钥
            base_url: API基础URL（默认OpenAI）
            timeout: 超时时间（秒）
            max_retries: 最大重试次数
        
        Raises:
            ImportError: 未安装openai库
        """
        if not HAS_OPENAI:
            raise ImportError(
                "使用LLMClient需要安装openai库:\n"
                "  uv pip install openai>=1.0.0"
            )
        
        self.api_key = api_key
        self.base_url = base_url
        self.timeout = timeout
        self.max_retries = max_retries
        
        # 初始化OpenAI客户端
        self.client = OpenAI(
            api_key=api_key,
            base_url=base_url,
            timeout=timeout,
            max_retries=max_retries,
        )
    
    def chat(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        model: str = "gpt-3.5-turbo",
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> str:
        """简单对话（仅返回文本内容）
        
        Args:
            prompt: 用户消息
            system_prompt: 系统提示（可选）
            model: 模型名称
            temperature: 温度参数 (0-2)
            max_tokens: 最大token数
            **kwargs: 其他OpenAI API参数
        
        Returns:
            生成的文本内容
        
        Example:
            >>> client = LLMClient(api_key="sk-...", base_url="...")
            >>> text = client.chat("介绍一下Python", model="gpt-4")
            >>> print(text)
        """
        messages = []
        if system_prompt:
            messages.append(Message(role="system", content=system_prompt))
        messages.append(Message(role="user", content=prompt))
        
        response = self.generate(
            messages=messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs
        )
        return response.content
    
    def generate(
        self,
        messages: List[Message],
        model: str = "gpt-3.5-turbo",
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> LLMResponse:
        """生成响应（返回完整信息）
        
        Args:
            messages: 消息列表
            model: 模型名称
            temperature: 温度参数
            max_tokens: 最大token数
            **kwargs: 其他OpenAI API参数
        
        Returns:
            LLM响应对象（包含token使用等信息）
        
        Raises:
            LLMTimeoutError: 调用超时
            LLMRateLimitError: 速率限制
            LLMAuthenticationError: 认证失败
            LLMAPIError: 其他API错误
        
        Example:
            >>> messages = [
            ...     Message(role="system", content="你是一个助手"),
            ...     Message(role="user", content="你好")
            ... ]
            >>> response = client.generate(messages, model="gpt-4")
            >>> print(f"内容: {response.content}")
            >>> print(f"Token: {response.total_tokens}")
        """
        # 转换消息格式
        openai_messages = [
            {"role": msg.role, "content": msg.content}
            for msg in messages
        ]
        
        try:
            start_time = time.time()
            
            # 调用OpenAI API（或兼容API）
            response = self.client.chat.completions.create(
                model=model,
                messages=openai_messages,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs
            )
            
            response_time = time.time() - start_time
            
            # 调试: 检查响应
            if response is None:
                raise LLMAPIError("API returned None response")
            
            # 检查是否有错误
            if hasattr(response, 'error') and response.error:
                error_msg = response.error.get('message', 'Unknown error')
                error_type = response.error.get('type', 'unknown')
                raise LLMAPIError(f"API error ({error_type}): {error_msg}")
            
            if not hasattr(response, 'choices') or not response.choices:
                raise LLMAPIError(f"API response has no choices: {response}")
            
            # 解析响应
            choice = response.choices[0]
            
            return LLMResponse(
                content=choice.message.content,
                model=response.model,
                prompt_tokens=response.usage.prompt_tokens if response.usage else None,
                completion_tokens=response.usage.completion_tokens if response.usage else None,
                total_tokens=response.usage.total_tokens if response.usage else None,
                finish_reason=choice.finish_reason,
                response_time=response_time,
            )
            
        except APITimeoutError as e:
            raise LLMTimeoutError(f"LLM调用超时: {e}") from e
        
        except RateLimitError as e:
            raise LLMRateLimitError(f"LLM速率限制: {e}") from e
        
        except OpenAIError as e:
            error_msg = str(e).lower()
            # 检测认证相关错误
            auth_keywords = ["authentication", "api_key", "api key", "unauthorized", "invalid api"]
            if any(keyword in error_msg for keyword in auth_keywords):
                raise LLMAuthenticationError(f"LLM认证失败: {e}") from e
            
            raise LLMAPIError(f"LLM API调用失败: {e}") from e
    
    def generate_with_retries(
        self,
        messages: List[Message],
        model: str = "gpt-3.5-turbo",
        max_retries: Optional[int] = None,
        **kwargs
    ) -> LLMResponse:
        """带重试的生成
        
        当调用失败时，会自动重试，使用指数退避策略
        
        Args:
            messages: 消息列表
            model: 模型名称
            max_retries: 最大重试次数（None则使用初始化时的值）
            **kwargs: 其他参数
        
        Returns:
            LLM响应
        
        Raises:
            LLMError: 所有重试都失败后抛出最后一个错误
        
        Example:
            >>> messages = [Message(role="user", content="Hello")]
            >>> # 自动重试，失败时指数退避（等待1s, 2s, 4s...）
            >>> response = client.generate_with_retries(messages, model="gpt-4")
        """
        max_retries = max_retries if max_retries is not None else self.max_retries
        last_error = None
        
        for attempt in range(max_retries):
            try:
                return self.generate(messages=messages, model=model, **kwargs)
            except (LLMTimeoutError, LLMAPIError, LLMRateLimitError) as e:
                last_error = e
                if attempt < max_retries - 1:
                    # 指数退避
                    wait_time = 2 ** attempt
                    time.sleep(wait_time)
                continue
        
        # 所有重试都失败
        raise last_error

