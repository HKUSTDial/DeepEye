#!/usr/bin/env python3
"""
在 backend 容器内运行，用当前 .env 的 AZURE_SPEECH_KEY / AZURE_SPEECH_REGION 测试 Azure TTS 是否可用。

用法（在项目根目录）:
  docker compose exec backend-worker python scripts/test_azure_tts.py
或:
  docker compose exec backend-api python scripts/test_azure_tts.py
"""
import sys
import tempfile
from pathlib import Path

# 确保能 import app（在容器内 PYTHONPATH 已包含 /app/packages/backend）
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

def main():
    from app.core.config import settings

    key = getattr(settings, "AZURE_SPEECH_KEY", None) or ""
    region = getattr(settings, "AZURE_SPEECH_REGION", None) or ""

    print("Azure TTS 配置检查")
    print("  AZURE_SPEECH_KEY: ", "已设置 (" + str(len(key)) + " 字符)" if key else "未设置")
    print("  AZURE_SPEECH_REGION:", repr(region) if region else "未设置")
    print()

    if not key or not region:
        print("错误: 请在 .env 中设置 AZURE_SPEECH_KEY 和 AZURE_SPEECH_REGION")
        return 1

    try:
        from app.node.video.config.audio_engine.tts_generator import TTSGenerator
    except ImportError as e:
        print("导入 TTSGenerator 失败:", e)
        return 1

    with tempfile.TemporaryDirectory() as tmpdir:
        try:
            generator = TTSGenerator(
                output_dir=tmpdir,
                api_key=key,
                region=region,
            )
            segment = generator.generate_audio(
                segment_id="test_azure_tts",
                text="Hello, this is a test.",
                language="en-US",
                verbose=True,
            )
            print()
            print("成功: Azure TTS 可用，生成的音频时长 %.2f 秒。" % segment.total_duration)
            return 0
        except Exception as e:
            print()
            print("失败:", type(e).__name__, str(e))
            import traceback
            traceback.print_exc()
            return 1

if __name__ == "__main__":
    sys.exit(main())
