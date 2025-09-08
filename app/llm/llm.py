import re
from typing import Any, Optional, List, Literal, Union, Dict
from tenacity import(
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_random_exponential
)
import threading
import tiktoken
from openai import (
    AsyncOpenAI,
    AsyncAzureOpenAI,
    OpenAIError,
    AuthenticationError,
    RateLimitError,
    BadRequestError
)
from openai.types.chat import ChatCompletionMessage
from app.config.config import config, LLMConfig
from .schema import Message
from app.logger import logger


class LLM:
    _client: AsyncOpenAI | AsyncAzureOpenAI = None
    _config_name: str = None
    _config: LLMConfig = None
    _instances: Dict[str, "LLM"] = {}
    _lock = threading.Lock()
    
    def __new__(cls, config_name: str = "default", llm_config: Optional[Dict[str, LLMConfig]] = None):
        if config_name not in cls._instances:
            with cls._lock:
                if config_name not in cls._instances:
                    instance = super().__new__(cls)
                    instance.__init__(config_name, llm_config)
                    cls._instances[config_name] = instance
        return cls._instances[config_name]
    
    def __init__(self, config_name: str = "default", llm_config: Optional[Dict[str, LLMConfig]] = None):
        llm_config = llm_config or config.llm_config
        self._config_name = config_name
        self._config = llm_config.get(config_name, llm_config["default"])
        self._client = self._create_client()
    
    def _create_client(self):
        if self._config.api_type == "openai":
            return AsyncOpenAI(api_key=self._config.api_key, base_url=self._config.base_url)
        elif self._config.api_type == "azure":
            return AsyncAzureOpenAI(api_key=self._config.api_key, base_url=self._config.base_url, api_version=self._config.api_version)

    @staticmethod
    def format_messages(messages: List[Union[Dict[str, str], Message]]) -> List[Dict[str, str]]:
        formatted_messages = []
        for message in messages:
            if isinstance(message, Message):
                formatted_messages.append(message.to_dict())
            elif isinstance(message, Dict):
                if "role" in message and ("content" in message or "tool_calls" in message):
                    formatted_messages.append(message)
                else:
                    raise ValueError(f"Unsupported message dict: {message}")
            else:
                raise ValueError(f"Unsupported message type: {type(message)}")
        return formatted_messages
        
    @retry(
        wait=wait_random_exponential(multiplier=1, max=60),
        stop=stop_after_attempt(6),
        retry=retry_if_exception_type(RateLimitError)
    )
    async def ask(self, 
                  messages: List[Union[Dict[str, str], Message]],
                  system_message: Optional[Union[Dict[str, str], Message]] = None,
                  timeout: int = 300,
                  tools: List[Dict[str, Any]] = None,
                  tool_choice: Literal["auto", "required", "none"] = "auto",
                  **kwargs) -> ChatCompletionMessage:
        try:
            if system_message:
                messages = [system_message] + messages
            messages = self.format_messages(messages)
            request_params = {
                "model": self._config.model,
                "messages": messages,
                "max_tokens": self._config.max_tokens,
                "temperature": self._config.temperature,
                "timeout": timeout,
            }
            request_params.update(kwargs)
        
            if tools:
                request_params["tools"] = tools
                request_params["tool_choice"] = tool_choice
                
            response = await self._client.chat.completions.create(**request_params)
            if not response.choices:
                raise OpenAIError(f"No response from the model: {response}")
            return response.choices[0].message
        except OpenAIError as e:
            if isinstance(e, RateLimitError):
                logger.error(f"OpenAI error: {e}")
                logger.error("Rate limit exceeded, please try again later.")
            elif isinstance(e, AuthenticationError):
                logger.error(f"OpenAI error: {e}")
                logger.error("Authentication error, please check your api key.")
            elif isinstance(e, BadRequestError):
                logger.error(f"OpenAI error: {e}")
                logger.error("Bad request, please check your request parameters.")
            raise e
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            raise e