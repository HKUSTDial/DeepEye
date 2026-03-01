"""
Audio Engine - 音频生成和时间同步引擎

这个模块负责：
1. 从配置文件生成 TTS 音频（支持 word-level timestamps）
2. 自动计算动画时间（基于旁白时间戳）
3. 将简化的配置转换为完整的带时间戳配置
"""

from .tts_generator import TTSGenerator, AudioSegment
from .time_aligner import TimeAligner, AlignedConfig
from .config_processor import ConfigProcessor

__all__ = [
    'TTSGenerator',
    'AudioSegment',
    'TimeAligner',
    'AlignedConfig',
    'ConfigProcessor',
]

