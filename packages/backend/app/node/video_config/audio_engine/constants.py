"""
Audio Engine 常量配置
"""

from app.core.config import settings

# 从项目配置系统导入 TTS API 配置（密钥和区域）
AZURE_SPEECH_KEY = settings.AZURE_SPEECH_KEY
AZURE_SPEECH_REGION = settings.AZURE_SPEECH_REGION

# 默认语音配置
DEFAULT_VOICE_CONFIG = {
    "en-US": {
        "voice_name": "en-US-AvaNeural",  # 专业讲故事风格
        "rate": "1.0",                     # 正常语速
        "pitch": "+0Hz",                   # 正常音调
    },
    "zh-CN": {
        "voice_name": "zh-CN-XiaoxiaoNeural",
        "rate": "1.0",
        "pitch": "+0Hz",
    },
}

# 输出路径配置
DEFAULT_AUDIO_OUTPUT_DIR = "public/audio"
DEFAULT_MANIFEST_FILE = "audio_manifest.json"

# 时间对齐配置
DEFAULT_ANIMATION_OFFSET = 0.0  # 动画相对于旁白的偏移（秒）
DEFAULT_ANIMATION_PADDING = 0.2  # 动画在旁白结束后的额外持续时间（秒）

# 缓动函数映射
EASING_FUNCTIONS = {
    "linear": "linear",
    "ease_in": "easeIn",
    "ease_out": "easeOut",
    "ease_in_out": "easeInOut",
    "ease_out_cubic": "cubic",
}

