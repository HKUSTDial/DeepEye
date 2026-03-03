#!/usr/bin/env python3
"""
测试音频时长检测逻辑

验证：
1. wave 模块能否正确读取 WAV 时长
2. ffprobe 是否可用（可选）
3. 不同采样率（24kHz/48kHz）的时长是否正确
4. 可选：真实 TTS 生成后时长是否正确

运行方式：
  uv run --package deepeye-backend python -m app.node.video.config.audio_engine.test_audio_duration

或在 Docker 内：
  docker compose exec backend-api python -m app.node.video.config.audio_engine.test_audio_duration
"""

import sys
import tempfile
import wave
from pathlib import Path

# 无额外 path 修改，依赖 PYTHONPATH（docker/uvicorn 已配置）


def create_test_wav(path: Path, duration_sec: float, sample_rate: int = 48000) -> None:
    """创建测试用 WAV 文件"""
    n_frames = int(duration_sec * sample_rate)
    with wave.open(str(path), 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)  # 16-bit
        wf.setframerate(sample_rate)
        # 静音数据
        wf.writeframes(b'\x00\x00' * n_frames)


def test_wave_module():
    """测试 wave 模块读取时长"""
    print("\n" + "=" * 60)
    print("1. 测试 wave 模块读取 WAV 时长")
    print("=" * 60)
    
    from app.node.video.config.audio_engine.tts_generator import TTSGenerator
    
    all_ok = True
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        
        # 测试 48kHz, 5 秒
        wav_48_5 = tmp / "test_48k_5s.wav"
        create_test_wav(wav_48_5, 5.0, 48000)
        dur = TTSGenerator._get_audio_duration(wav_48_5)
        ok = abs(dur - 5.0) < 0.01
        all_ok = all_ok and ok
        print(f"   48kHz 5秒: 期望 5.0s, 得到 {dur:.3f}s -> {'✓ 通过' if ok else '✗ 失败'}")
        
        # 测试 24kHz, 10 秒
        wav_24_10 = tmp / "test_24k_10s.wav"
        create_test_wav(wav_24_10, 10.0, 24000)
        dur = TTSGenerator._get_audio_duration(wav_24_10)
        ok = abs(dur - 10.0) < 0.01
        all_ok = all_ok and ok
        print(f"   24kHz 10秒: 期望 10.0s, 得到 {dur:.3f}s -> {'✓ 通过' if ok else '✗ 失败'}")
        
        # 测试 44.1kHz, 3.5 秒
        wav_44_35 = tmp / "test_44k_3.5s.wav"
        create_test_wav(wav_44_35, 3.5, 44100)
        dur = TTSGenerator._get_audio_duration(wav_44_35)
        ok = abs(dur - 3.5) < 0.01
        all_ok = all_ok and ok
        print(f"   44.1kHz 3.5秒: 期望 3.5s, 得到 {dur:.3f}s -> {'✓ 通过' if ok else '✗ 失败'}")
    
    print("   wave 模块测试完成")
    return all_ok


def test_ffprobe_available():
    """检查 ffprobe 是否可用"""
    print("\n" + "=" * 60)
    print("2. 检查 ffprobe 是否可用")
    print("=" * 60)
    
    import subprocess
    try:
        r = subprocess.run(
            ['ffprobe', '-version'],
            capture_output=True,
            text=True,
            timeout=3,
        )
        if r.returncode == 0:
            first_line = r.stdout.split('\n')[0] if r.stdout else ''
            print(f"   ✓ ffprobe 可用: {first_line}")
            return True
        else:
            print("   ✗ ffprobe 存在但执行失败")
            return False
    except FileNotFoundError:
        print("   ✗ ffprobe 未安装（不影响：优先使用 wave 模块）")
        return False
    except Exception as e:
        print(f"   ✗ ffprobe 检查异常: {e}")
        return False


def test_real_tts_if_configured():
    """如果配置了 Azure，执行一次真实 TTS 并检查时长"""
    print("\n" + "=" * 60)
    print("3. 可选：真实 TTS 生成测试")
    print("=" * 60)
    
    try:
        from app.core.config import settings
        api_key = getattr(settings, 'AZURE_SPEECH_KEY', None) or ''
        region = getattr(settings, 'AZURE_SPEECH_REGION', None) or ''
        if not api_key or not region:
            print("   跳过: 未配置 AZURE_SPEECH_KEY / AZURE_SPEECH_REGION")
            return True
    except Exception as ex:
        print(f"   跳过: 无法加载 settings ({ex})")
        return True
    
    from app.node.video.config.audio_engine import TTSGenerator
    
    with tempfile.TemporaryDirectory() as tmpdir:
        gen = TTSGenerator(
            output_dir=tmpdir,
            api_key=api_key,
            region=region,
        )
        text = "这是一句测试文本，用于验证音频时长检测是否正确。"  # 约 4-6 秒
        print(f"   生成 TTS: \"{text[:30]}...\"")
        try:
            seg = gen.generate_audio(
                segment_id="test_duration",
                text=text,
                language="zh-CN",
                verbose=True,
            )
            dur = seg.total_duration
            # 这句中文正常朗读约 4-7 秒
            ok = 3.0 <= dur <= 15.0
            print(f"   得到时长: {dur:.2f}s -> {'✓ 合理' if ok else '⚠ 异常（预期约 4-7 秒）'}")
            return ok
        except Exception as e:
            print(f"   ✗ TTS 生成失败: {e}")
            return False


def main():
    print("\n" + "#" * 60)
    print("# 音频时长检测测试")
    print("#" * 60)
    
    all_ok = True
    
    all_ok = test_wave_module() and all_ok
    test_ffprobe_available()  # 仅检查，不影响 all_ok
    
    try:
        all_ok = test_real_tts_if_configured() and all_ok
    except Exception as e:
        print(f"   TTS 测试异常: {e}")
    
    print("\n" + "=" * 60)
    if all_ok:
        print("✓ 所有测试通过，音频时长检测可用")
    else:
        print("✗ 部分测试失败，请检查")
    print("=" * 60 + "\n")
    
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
