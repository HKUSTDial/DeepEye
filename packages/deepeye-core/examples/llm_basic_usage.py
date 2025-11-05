"""LLM客户端基础使用示例

展示如何使用DeepEye的LLM客户端调用不同的LLM提供商
"""

import os
os.environ["OPENAI_API_KEY"] = "sk-7831f4d991724beeb34733758d8d3274"
os.environ["OPENAI_BASE_URL"] = "https://dashscope.aliyuncs.com/compatible-mode/v1"

from deepeye.llm import LLMClient, Message


def example_1_simple_chat():
    """示例1: 简单对话"""
    print("=" * 80)
    print("示例1: 简单对话")
    print("=" * 80)
    print()
    
    # 注意：需要设置环境变量 OPENAI_API_KEY
    api_key = os.getenv("OPENAI_API_KEY", "sk-...")
    
    if api_key == "sk-...":
        print("⚠️  请设置环境变量 OPENAI_API_KEY")
        print("   export OPENAI_API_KEY=sk-...")
        return
    
    # 创建客户端
    client = LLMClient(
        api_key=api_key,
        base_url="https://api.openai.com/v1"
    )
    
    # 简单对话
    response = client.chat(
        "用一句话介绍Python的主要优势",
        model="gpt-3.5-turbo"
    )
    
    print(f"💬 问题: 用一句话介绍Python的主要优势")
    print(f"🤖 回答: {response}")
    print()


def example_2_with_system_prompt():
    """示例2: 使用系统提示"""
    print("=" * 80)
    print("示例2: 使用系统提示")
    print("=" * 80)
    print()
    
    api_key = os.getenv("OPENAI_API_KEY", "sk-...")
    if api_key == "sk-...":
        print("⚠️  请设置环境变量 OPENAI_API_KEY")
        return
    
    client = LLMClient(api_key=api_key)
    
    # 带系统提示的对话
    response = client.chat(
        prompt="写一个快速排序",
        system_prompt="你是一个Python编程专家，回答要简洁",
        model="gpt-3.5-turbo",
        temperature=0.1  # 较低的温度，更确定的输出
    )
    
    print(f"💬 问题: 写一个快速排序")
    print(f"🤖 回答:\n{response}")
    print()


def example_3_full_response():
    """示例3: 获取完整响应信息"""
    print("=" * 80)
    print("示例3: 获取完整响应信息（包含Token使用）")
    print("=" * 80)
    print()
    
    api_key = os.getenv("OPENAI_API_KEY", "sk-...")
    if api_key == "sk-...":
        print("⚠️  请设置环境变量 OPENAI_API_KEY")
        return
    
    client = LLMClient(api_key=api_key)
    
    # 使用generate方法获取完整信息
    messages = [
        Message(role="system", content="你是一个助手"),
        Message(role="user", content="什么是机器学习？")
    ]
    
    response = client.generate(messages, model="gpt-3.5-turbo")
    
    print(f"💬 问题: 什么是机器学习？")
    print(f"🤖 回答: {response.content}")
    print()
    print("📊 元信息:")
    print(f"  - 模型: {response.model}")
    print(f"  - Prompt Tokens: {response.prompt_tokens}")
    print(f"  - Completion Tokens: {response.completion_tokens}")
    print(f"  - Total Tokens: {response.total_tokens}")
    print(f"  - 耗时: {response.response_time:.2f}秒")
    print(f"  - 完成原因: {response.finish_reason}")
    print()


def example_4_qwen():
    """示例4: 使用通义千问"""
    print("=" * 80)
    print("示例4: 使用通义千问（Qwen）")
    print("=" * 80)
    print()
    
    api_key = os.getenv("QWEN_API_KEY", "sk-...")
    if api_key == "sk-...":
        print("⚠️  请设置环境变量 QWEN_API_KEY")
        print("   获取API Key: https://dashscope.aliyun.com/")
        return
    
    # 创建通义千问客户端（只需改base_url）
    client = LLMClient(
        api_key=api_key,
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
    )
    
    response = client.chat(
        "介绍一下阿里云的产品",
        model="qwen-turbo"  # 或 qwen-plus, qwen-max
    )
    
    print(f"💬 问题: 介绍一下阿里云的产品")
    print(f"🤖 回答: {response}")
    print()


def example_5_ollama():
    """示例5: 使用本地Ollama模型"""
    print("=" * 80)
    print("示例5: 使用本地Ollama模型")
    print("=" * 80)
    print()
    
    print("ℹ️  此示例需要先安装并启动Ollama:")
    print("   1. 安装: https://ollama.ai/")
    print("   2. 下载模型: ollama pull llama2")
    print("   3. 启动服务（自动运行）")
    print()
    
    try:
        # 创建Ollama客户端
        client = LLMClient(
            api_key="ollama",  # Ollama不需要真实key
            base_url="http://localhost:11434/v1",
            timeout=30
        )
        
        response = client.chat(
            "Hello, how are you?",
            model="llama2"
        )
        
        print(f"💬 问题: Hello, how are you?")
        print(f"🤖 回答: {response}")
        print()
        
    except Exception as e:
        print(f"❌ 连接Ollama失败: {e}")
        print("   请确保Ollama服务正在运行")
        print()


def example_6_error_handling():
    """示例6: 错误处理"""
    print("=" * 80)
    print("示例6: 错误处理和重试")
    print("=" * 80)
    print()
    
    from deepeye.llm.exceptions import (
        LLMAuthenticationError,
        LLMAPIError,
        LLMTimeoutError
    )
    
    # 1. 认证错误
    print("测试1: 错误的API Key")
    try:
        client = LLMClient(api_key="invalid-key")
        response = client.chat("Hello")
    except LLMAuthenticationError as e:
        print(f"✅ 成功捕获认证错误: {e}")
    except Exception as e:
        print(f"⚠️  捕获其他错误: {type(e).__name__}: {e}")
    print()
    
    # 2. 使用重试机制
    print("测试2: 带重试的调用")
    api_key = os.getenv("OPENAI_API_KEY", "sk-...")
    if api_key != "sk-...":
        client = LLMClient(api_key=api_key, max_retries=3)
        messages = [Message(role="user", content="Say hi")]
        
        try:
            # generate_with_retries会在失败时自动重试
            response = client.generate_with_retries(messages)
            print(f"✅ 调用成功: {response.content[:50]}...")
        except LLMAPIError as e:
            print(f"❌ 所有重试都失败: {e}")
    print()


def example_7_multi_turn_conversation():
    """示例7: 多轮对话"""
    print("=" * 80)
    print("示例7: 多轮对话")
    print("=" * 80)
    print()
    
    api_key = os.getenv("OPENAI_API_KEY", "sk-...")
    if api_key == "sk-...":
        print("⚠️  请设置环境变量 OPENAI_API_KEY")
        return
    
    client = LLMClient(api_key=api_key)
    
    # 维护对话历史
    messages = [
        Message(role="system", content="你是一个Python教学助手")
    ]
    
    # 第一轮
    messages.append(Message(role="user", content="什么是列表推导式？"))
    response = client.generate(messages, model="gpt-3.5-turbo", temperature=0.3)
    messages.append(Message(role="assistant", content=response.content))
    
    print("👤 用户: 什么是列表推导式？")
    print(f"🤖 助手: {response.content}")
    print()
    
    # 第二轮（基于上下文）
    messages.append(Message(role="user", content="给我一个例子"))
    response = client.generate(messages, model="gpt-3.5-turbo", temperature=0.3)
    
    print("👤 用户: 给我一个例子")
    print(f"🤖 助手: {response.content}")
    print()


def main():
    """运行所有示例"""
    print("\n")
    print("🚀 DeepEye LLM客户端使用示例")
    print("=" * 80)
    print()
    
    # 运行示例
    example_1_simple_chat()
    example_2_with_system_prompt()
    example_3_full_response()
    example_4_qwen()
    example_5_ollama()
    example_6_error_handling()
    example_7_multi_turn_conversation()
    
    print("=" * 80)
    print("✅ 所有示例运行完成！")
    print()
    print("💡 提示:")
    print("  - 设置环境变量以使用真实API: export OPENAI_API_KEY=sk-...")
    print("  - 支持的提供商: OpenAI, 通义千问, DeepSeek, Moonshot, 智谱AI, Ollama")
    print("  - 只需修改 base_url 即可切换提供商")
    print()


if __name__ == "__main__":
    main()

