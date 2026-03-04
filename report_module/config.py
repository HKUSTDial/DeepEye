# config.py
import os

# 建议使用环境变量，这里保留默认值方便测试
API_KEY = os.getenv("OPENAI_API_KEY", "sk-z38TPP3SlXtHNj3tsnf8rSEHS0xqKCQxglXHSUHlQzutV6rB")
BASE_URL = os.getenv("OPENAI_BASE_URL", "https://www.chatgtp.cn/v1")
MODEL_NAME = "gpt-4o"