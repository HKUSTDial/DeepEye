"""测试LLM客户端"""

import pytest
from unittest.mock import Mock, patch, MagicMock

from deepeye.llm import LLMClient, Message, LLMResponse
from deepeye.llm.exceptions import (
    LLMAPIError,
    LLMTimeoutError,
    LLMRateLimitError,
    LLMAuthenticationError,
)


@pytest.fixture
def mock_openai():
    """Mock OpenAI客户端"""
    with patch('deepeye.llm.client.OpenAI') as mock:
        # 创建mock响应
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message = Mock()
        mock_response.choices[0].message.content = "Test response content"
        mock_response.choices[0].finish_reason = "stop"
        
        # Mock usage
        mock_response.usage = Mock()
        mock_response.usage.prompt_tokens = 10
        mock_response.usage.completion_tokens = 20
        mock_response.usage.total_tokens = 30
        
        mock_response.model = "gpt-4"
        
        # 配置mock client
        mock_client_instance = Mock()
        mock_client_instance.chat.completions.create.return_value = mock_response
        mock.return_value = mock_client_instance
        
        yield mock


class TestLLMClientInit:
    """测试LLMClient初始化"""
    
    def test_init_with_defaults(self, mock_openai):
        """测试使用默认参数初始化"""
        client = LLMClient(api_key="test-key")
        
        assert client.api_key == "test-key"
        assert client.base_url == "https://api.openai.com/v1"
        assert client.timeout == 60
        assert client.max_retries == 3
    
    def test_init_with_custom_params(self, mock_openai):
        """测试使用自定义参数初始化"""
        client = LLMClient(
            api_key="custom-key",
            base_url="https://custom.api.com/v1",
            timeout=120,
            max_retries=5
        )
        
        assert client.api_key == "custom-key"
        assert client.base_url == "https://custom.api.com/v1"
        assert client.timeout == 120
        assert client.max_retries == 5


class TestMessage:
    """测试Message数据类"""
    
    def test_message_creation(self):
        """测试消息创建"""
        msg = Message(role="user", content="Hello")
        assert msg.role == "user"
        assert msg.content == "Hello"
    
    def test_message_system_role(self):
        """测试系统角色消息"""
        msg = Message(role="system", content="You are a helpful assistant")
        assert msg.role == "system"
        assert msg.content == "You are a helpful assistant"


class TestLLMResponse:
    """测试LLMResponse数据类"""
    
    def test_response_creation(self):
        """测试响应创建"""
        response = LLMResponse(
            content="Test",
            model="gpt-4",
            prompt_tokens=10,
            completion_tokens=20,
            total_tokens=30,
            finish_reason="stop",
            response_time=1.23
        )
        
        assert response.content == "Test"
        assert response.model == "gpt-4"
        assert response.total_tokens == 30
        assert response.response_time == 1.23


class TestLLMClientChat:
    """测试chat方法"""
    
    def test_chat_simple(self, mock_openai):
        """测试简单对话"""
        client = LLMClient(api_key="test-key")
        response = client.chat("Hello", model="gpt-4")
        
        assert response == "Test response content"
        
        # 验证调用参数
        mock_openai.return_value.chat.completions.create.assert_called_once()
        call_args = mock_openai.return_value.chat.completions.create.call_args
        assert call_args[1]["model"] == "gpt-4"
        assert len(call_args[1]["messages"]) == 1
        assert call_args[1]["messages"][0]["content"] == "Hello"
    
    def test_chat_with_system_prompt(self, mock_openai):
        """测试带系统提示的对话"""
        client = LLMClient(api_key="test-key")
        response = client.chat(
            "Hello",
            system_prompt="You are a helpful assistant",
            model="gpt-4"
        )
        
        assert response == "Test response content"
        
        # 验证有两条消息
        call_args = mock_openai.return_value.chat.completions.create.call_args
        assert len(call_args[1]["messages"]) == 2
        assert call_args[1]["messages"][0]["role"] == "system"
        assert call_args[1]["messages"][1]["role"] == "user"
    
    def test_chat_with_temperature(self, mock_openai):
        """测试指定温度参数"""
        client = LLMClient(api_key="test-key")
        response = client.chat("Hello", temperature=0.1)
        
        assert response == "Test response content"
        
        call_args = mock_openai.return_value.chat.completions.create.call_args
        assert call_args[1]["temperature"] == 0.1


class TestLLMClientGenerate:
    """测试generate方法"""
    
    def test_generate_with_messages(self, mock_openai):
        """测试使用消息列表生成"""
        client = LLMClient(api_key="test-key")
        messages = [
            Message(role="system", content="You are a helper"),
            Message(role="user", content="Hello")
        ]
        
        response = client.generate(messages, model="gpt-4")
        
        assert isinstance(response, LLMResponse)
        assert response.content == "Test response content"
        assert response.model == "gpt-4"
        assert response.total_tokens == 30
        assert response.prompt_tokens == 10
        assert response.completion_tokens == 20
        assert response.finish_reason == "stop"
        assert response.response_time > 0
    
    def test_generate_with_max_tokens(self, mock_openai):
        """测试指定最大token数"""
        client = LLMClient(api_key="test-key")
        messages = [Message(role="user", content="Test")]
        
        response = client.generate(messages, max_tokens=100)
        
        call_args = mock_openai.return_value.chat.completions.create.call_args
        assert call_args[1]["max_tokens"] == 100
    
    def test_generate_without_usage(self, mock_openai):
        """测试API返回中没有usage信息的情况"""
        # 修改mock，移除usage
        mock_response = mock_openai.return_value.chat.completions.create.return_value
        mock_response.usage = None
        
        client = LLMClient(api_key="test-key")
        messages = [Message(role="user", content="Test")]
        
        response = client.generate(messages)
        
        assert response.prompt_tokens is None
        assert response.completion_tokens is None
        assert response.total_tokens is None


class TestLLMClientErrorHandling:
    """测试错误处理"""
    
    def test_timeout_error(self, mock_openai):
        """测试超时错误"""
        from openai import APITimeoutError
        
        mock_openai.return_value.chat.completions.create.side_effect = APITimeoutError(
            request=Mock()
        )
        
        client = LLMClient(api_key="test-key")
        messages = [Message(role="user", content="Test")]
        
        with pytest.raises(LLMTimeoutError) as exc_info:
            client.generate(messages)
        
        assert "超时" in str(exc_info.value)
    
    def test_rate_limit_error(self, mock_openai):
        """测试速率限制错误"""
        from openai import RateLimitError
        
        mock_openai.return_value.chat.completions.create.side_effect = RateLimitError(
            response=Mock(),
            body=None,
            message="Rate limit exceeded"
        )
        
        client = LLMClient(api_key="test-key")
        messages = [Message(role="user", content="Test")]
        
        with pytest.raises(LLMRateLimitError) as exc_info:
            client.generate(messages)
        
        assert "速率限制" in str(exc_info.value)
    
    def test_authentication_error(self, mock_openai):
        """测试认证错误"""
        from openai import OpenAIError
        
        mock_openai.return_value.chat.completions.create.side_effect = OpenAIError(
            "Invalid API key"
        )
        
        client = LLMClient(api_key="test-key")
        messages = [Message(role="user", content="Test")]
        
        with pytest.raises(LLMAuthenticationError):
            client.generate(messages)
    
    def test_generic_api_error(self, mock_openai):
        """测试通用API错误"""
        from openai import OpenAIError
        
        mock_openai.return_value.chat.completions.create.side_effect = OpenAIError(
            "Some generic error"
        )
        
        client = LLMClient(api_key="test-key")
        messages = [Message(role="user", content="Test")]
        
        with pytest.raises(LLMAPIError):
            client.generate(messages)


class TestLLMClientRetries:
    """测试重试机制"""
    
    def test_retry_success_on_second_attempt(self, mock_openai):
        """测试第二次重试成功"""
        from openai import OpenAIError
        
        # 第一次失败，第二次成功
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message = Mock()
        mock_response.choices[0].message.content = "Success"
        mock_response.choices[0].finish_reason = "stop"
        mock_response.usage = Mock()
        mock_response.usage.prompt_tokens = 10
        mock_response.usage.completion_tokens = 20
        mock_response.usage.total_tokens = 30
        mock_response.model = "gpt-4"
        
        mock_openai.return_value.chat.completions.create.side_effect = [
            OpenAIError("Temporary error"),
            mock_response
        ]
        
        client = LLMClient(api_key="test-key", max_retries=3)
        messages = [Message(role="user", content="Test")]
        
        response = client.generate_with_retries(messages)
        
        assert response.content == "Success"
        # 验证调用了2次
        assert mock_openai.return_value.chat.completions.create.call_count == 2
    
    def test_retry_all_failed(self, mock_openai):
        """测试所有重试都失败"""
        from openai import OpenAIError
        
        mock_openai.return_value.chat.completions.create.side_effect = OpenAIError(
            "Permanent error"
        )
        
        client = LLMClient(api_key="test-key", max_retries=3)
        messages = [Message(role="user", content="Test")]
        
        with pytest.raises(LLMAPIError):
            client.generate_with_retries(messages)
        
        # 验证调用了3次
        assert mock_openai.return_value.chat.completions.create.call_count == 3
    
    def test_retry_custom_max_retries(self, mock_openai):
        """测试自定义最大重试次数"""
        from openai import OpenAIError
        
        mock_openai.return_value.chat.completions.create.side_effect = OpenAIError(
            "Error"
        )
        
        client = LLMClient(api_key="test-key", max_retries=3)
        messages = [Message(role="user", content="Test")]
        
        with pytest.raises(LLMAPIError):
            # 覆盖max_retries为2
            client.generate_with_retries(messages, max_retries=2)
        
        # 验证只调用了2次
        assert mock_openai.return_value.chat.completions.create.call_count == 2

