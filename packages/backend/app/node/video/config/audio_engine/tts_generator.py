#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TTS Generator - 支持 Word-Level Timestamps 的 TTS 音频生成器

核心功能：
1. 从文本生成音频（Azure Neural TTS）
2. 捕获每个词的开始/结束时间戳
3. 输出结构化的音频元数据

参考：Data Player 论文 Section 4.3 - Narration-Animation Interplay
"""

import json
import subprocess
import time
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, asdict
from concurrent.futures import ThreadPoolExecutor, as_completed

try:
    import azure.cognitiveservices.speech as speechsdk
except ImportError:
    print("⚠️  Warning: azure-cognitiveservices-speech not installed")
    print("   Install: pip install azure-cognitiveservices-speech")
    speechsdk = None

from .constants import (
    AZURE_SPEECH_KEY,
    AZURE_SPEECH_REGION,
    DEFAULT_VOICE_CONFIG,
    DEFAULT_AUDIO_OUTPUT_DIR,
)


@dataclass
class WordTimestamp:
    """单个词的时间戳"""
    word: str           # 词文本
    start: float        # 开始时间（秒）
    end: float          # 结束时间（秒）
    duration: float     # 持续时间（秒）


@dataclass
class AudioSegment:
    """音频片段（对应一个场景的旁白）"""
    segment_id: str                 # 片段ID（如 "scene1"）
    text: str                       # 完整文本
    audio_file: str                 # 音频文件路径
    total_duration: float           # 总时长（秒）
    words: List[WordTimestamp]      # 词级别时间戳
    language: str = "en-US"         # 语言
    
    def to_dict(self) -> dict:
        """转换为字典（用于JSON序列化）"""
        return {
            'segment_id': self.segment_id,
            'text': self.text,
            'audio_file': self.audio_file,
            'total_duration': round(self.total_duration, 3),
            'language': self.language,
            'words': [asdict(w) for w in self.words],
        }


class TTSGenerator:
    """TTS 音频生成器"""
    
    def __init__(
        self,
        output_dir: str = DEFAULT_AUDIO_OUTPUT_DIR,
        voice_config: Optional[Dict] = None,
        api_key: Optional[str] = None,
        region: Optional[str] = None,
    ):
        """
        初始化 TTS 生成器
        
        Args:
            output_dir: 音频输出目录
            voice_config: 语音配置（覆盖默认配置）
            api_key: Azure API Key（可选，默认使用常量）
            region: Azure 区域（可选，默认使用常量）
        """
        self.output_dir = Path(output_dir).resolve()  # 转为绝对路径
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.api_key = api_key or AZURE_SPEECH_KEY
        self.region = region or AZURE_SPEECH_REGION
        self.voice_config = voice_config or DEFAULT_VOICE_CONFIG
        
        if not self.api_key:
            raise ValueError("Azure Speech API key is required")
        
        if speechsdk is None:
            raise ImportError(
                "azure-cognitiveservices-speech is required. "
                "Install: pip install azure-cognitiveservices-speech"
            )
    
    def generate_audio(
        self,
        segment_id: str,
        text: str,
        language: str = "en-US",
        ssml: Optional[str] = None,
        verbose: bool = True,
        max_retries: int = 3,
        retry_delay: float = 2.0,
        max_retry_time: float = 600.0,  # 最大重试时间（秒），默认10分钟
    ) -> AudioSegment:
        """
        生成单个音频片段（支持 word-level timestamps，带重试机制）
        
        Args:
            segment_id: 片段ID（如 "scene1_narration1"）
            text: 文本内容
            language: 语言代码
            ssml: 可选的 SSML（如果提供，将使用 SSML 而非纯文本）
            verbose: 是否打印详细信息
            max_retries: 最大重试次数（仅用于非关键错误，默认3次）
            retry_delay: 重试延迟（秒，默认2秒）
            max_retry_time: 最大重试时间（秒，默认600秒=10分钟）
        
        Returns:
            AudioSegment: 包含音频文件路径和 word timestamps
            
        注意：
            - 429 Rate Limit：无限重试（直到 max_retry_time）
            - 网络连接错误：无限重试（直到 max_retry_time）
            - 超时错误：无限重试（直到 max_retry_time）
            - 其他错误：立即失败
        """
        attempt = 0
        start_time = time.time()
        
        while True:  # 无限重试（直到时间限制）
            try:
                if verbose and attempt > 0:
                    # 429错误会无限重试，所以显示尝试次数而不是总数
                    print(f"🔄 Retrying {segment_id} (attempt {attempt + 1})...")
                elif verbose:
                    print(f"🎙️  Generating audio for {segment_id}...")
                
                # 配置输出文件
                audio_file = self.output_dir / f"{segment_id}.wav"
                
                # 配置 Azure Speech
                speech_config = speechsdk.SpeechConfig(
                    subscription=self.api_key,
                    region=self.region
                )
                
                # 设置语音
                voice_cfg = self.voice_config.get(language, DEFAULT_VOICE_CONFIG["en-US"])
                speech_config.speech_synthesis_voice_name = voice_cfg["voice_name"]
                
                # 配置音频输出
                audio_config = speechsdk.audio.AudioOutputConfig(filename=str(audio_file))
                
                # 创建合成器
                synthesizer = speechsdk.SpeechSynthesizer(
                    speech_config=speech_config,
                    audio_config=audio_config
                )
                
                # 用于收集 word boundaries
                word_timestamps: List[WordTimestamp] = []
                
                def word_boundary_callback(evt):
                    """捕获每个词的边界事件"""
                    try:
                        # evt.audio_offset 可能是 timedelta 或整数（100ns 为单位）
                        # evt.duration 是 timedelta 对象
                        # 统一转换为秒
                        if hasattr(evt.audio_offset, 'total_seconds'):
                            start_time = evt.audio_offset.total_seconds()
                        else:
                            start_time = evt.audio_offset / 10_000_000.0
                        
                        if hasattr(evt.duration, 'total_seconds'):
                            duration_time = evt.duration.total_seconds()
                        else:
                            duration_time = evt.duration / 10_000_000.0
                        
                        end_time = start_time + duration_time
                        
                        word_timestamps.append(WordTimestamp(
                            word=evt.text,
                            start=round(start_time, 3),
                            end=round(end_time, 3),
                            duration=round(duration_time, 3),
                        ))
                        
                        if verbose:
                            print(f"      🎯 Word: {evt.text} @ {start_time:.3f}s")
                    except Exception as e:
                        print(f"⚠️  Warning: Failed to capture word boundary for '{evt.text}': {e}")
                
                # 注册事件监听器
                synthesizer.synthesis_word_boundary.connect(word_boundary_callback)
                
                # 生成语音
                if ssml:
                    result = synthesizer.speak_ssml_async(ssml).get()
                else:
                    result = synthesizer.speak_text_async(text).get()
                
                # 检查结果
                if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
                    total_duration = self._get_audio_duration(audio_file)
                    
                    # 保存相对于 public/ 目录的路径（如 "public/audio/scene1.wav"）
                    # 这样配置文件可以在任何地方被正确读取
                    try:
                        # 尝试相对于 output_dir 的父目录（public/）
                        relative_path = audio_file.relative_to(self.output_dir.parent.parent)
                        audio_file_str = str(relative_path)
                    except ValueError:
                        # 如果无法计算相对路径，使用绝对路径
                        audio_file_str = str(audio_file)
                    
                    segment = AudioSegment(
                        segment_id=segment_id,
                        text=text,
                        audio_file=audio_file_str,
                        total_duration=total_duration,
                        words=word_timestamps,
                        language=language,
                    )
                    
                    if verbose:
                        print(f"   ✅ Generated: {audio_file.name} ({total_duration:.2f}s, {len(word_timestamps)} words)")
                    return segment
                else:
                    error_msg = f"TTS failed: {result.reason}"
                    if result.reason == speechsdk.ResultReason.Canceled:
                        cancellation = result.cancellation_details
                        error_msg += f" - {cancellation.reason}: {cancellation.error_details}"
                    
                    # 检查错误类型
                    error_msg_lower = error_msg.lower()
                    is_rate_limit = "429" in error_msg or "too many requests" in error_msg_lower
                    is_timeout = "timeout" in error_msg_lower or "usp error" in error_msg
                    # 网络连接错误：connection failed, connection error, ws_open_error, network error
                    is_network_error = (
                        "connection failed" in error_msg_lower or
                        "connection error" in error_msg_lower or
                        "ws_open_error" in error_msg_lower or
                        "network error" in error_msg_lower or
                        "no connection" in error_msg_lower
                    )
                    
                    # 检查是否超过最大重试时间
                    elapsed_time = time.time() - start_time
                    if elapsed_time > max_retry_time:
                        raise RuntimeError(f"TTS failed: exceeded max retry time ({max_retry_time/60:.1f} minutes) - {error_msg}")
                    
                    if is_rate_limit:
                        # 429错误：无限重试 + 指数退避（直到 max_retry_time）
                        # 延迟时间：2s, 4s, 8s, 16s, ... (最大60s)
                        delay = min(retry_delay * (2 ** min(attempt, 4)), 60.0)
                        if verbose:
                            print(f"   ⚠️  Rate limit (429), retry after {delay:.1f}s... (attempt {attempt + 1}, elapsed: {elapsed_time:.0f}s)")
                        time.sleep(delay)
                        attempt += 1
                        continue
                    elif is_timeout or is_network_error:
                        # 超时/网络错误：无限重试 + 固定延迟（直到 max_retry_time）
                        # 这些都是临时性错误，值得一直重试，因为音频生成失败意味着整个视频白费
                        error_type = "Network connection" if is_network_error else "Timeout"
                        if verbose:
                            print(f"   ⚠️  {error_type} error, retry after {retry_delay}s... (attempt {attempt + 1}, elapsed: {elapsed_time:.0f}s)")
                        time.sleep(retry_delay)
                        attempt += 1
                        continue
                    else:
                        # 其他错误（永久性错误），直接抛出
                        raise RuntimeError(error_msg)
            
            except RuntimeError:
                # RuntimeError 已经在上面处理过（429/超时已重试或抛出，其他直接抛出）
                raise
            except Exception as e:
                # 检查是否是429、超时或网络连接相关错误（来自异常消息）
                error_str = str(e).lower()
                is_rate_limit = "429" in str(e) or "too many requests" in error_str
                is_timeout = "timeout" in error_str or "usp error" in error_str
                # 网络连接错误：connection failed, connection error, ws_open_error, network error
                is_network_error = (
                    "connection failed" in error_str or
                    "connection error" in error_str or
                    "ws_open_error" in error_str or
                    "network error" in error_str or
                    "no connection" in error_str
                )
                
                # 检查是否超过最大重试时间
                elapsed_time = time.time() - start_time
                if elapsed_time > max_retry_time:
                    raise RuntimeError(f"TTS failed: exceeded max retry time ({max_retry_time/60:.1f} minutes) - {e}")
                
                if is_rate_limit:
                    # 429错误：无限重试 + 指数退避（直到 max_retry_time）
                    delay = min(retry_delay * (2 ** min(attempt, 4)), 60.0)
                    if verbose:
                        print(f"   ⚠️  Rate limit (429), retry after {delay:.1f}s... (attempt {attempt + 1}, elapsed: {elapsed_time:.0f}s)")
                    time.sleep(delay)
                    attempt += 1
                    continue
                elif is_timeout or is_network_error:
                    # 超时/网络错误：无限重试 + 固定延迟（直到 max_retry_time）
                    error_type = "Network connection" if is_network_error else "Timeout"
                    if verbose:
                        print(f"   ⚠️  {error_type} error, retry after {retry_delay}s... (attempt {attempt + 1}, elapsed: {elapsed_time:.0f}s)")
                    time.sleep(retry_delay)
                    attempt += 1
                    continue
                else:
                    # 非超时/网络错误，直接抛出
                    raise
    
    def generate_batch(
        self,
        narrations: List[Dict],
        language: str = "en-US",
        verbose: bool = True,
        max_workers: int = 2,
    ) -> List[AudioSegment]:
        """
        批量生成音频片段（并行处理）
        
        Args:
            narrations: 旁白列表，每个元素应包含:
                - id: 片段ID
                - text: 文本内容
                - ssml: （可选）SSML
            language: 语言代码
            verbose: 是否打印详细信息
            max_workers: 最大并发数（默认2，避免触发API限制和超时）
        
        Returns:
            List[AudioSegment]: 生成的音频片段列表（保持输入顺序）
        """
        total = len(narrations)
        if total == 0:
            return []
        
        # 准备任务列表（包含索引以保持顺序）
        tasks = []
        for idx, narr in enumerate(narrations):
            segment_id = narr.get('id') or narr.get('segment_id', f"segment_{idx}")
            text = narr['text']
            ssml = narr.get('ssml')
            tasks.append((idx, segment_id, text, ssml))
        
        # 用于存储结果的字典（按索引）
        results = {}
        completed_count = 0
        
        if verbose:
            print(f"\n🚀 Starting parallel audio generation")
            print(f"   Workers: {max_workers}, Total segments: {total}")
            print(f"   Progress: [{' ' * 50}] 0%")
        
        # 使用线程池并行生成
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 提交所有任务（添加小延迟避免同时发起太多请求）
            future_to_task = {}
            for idx, segment_id, text, ssml in tasks:
                # 添加小延迟，避免同时发起太多请求导致超时
                if idx > 0 and idx % max_workers == 0:
                    time.sleep(0.5)
                
                future = executor.submit(
                    self._generate_audio_safe,
                    segment_id, text, language, ssml, idx
                )
                future_to_task[future] = (idx, segment_id)
            
            # 处理完成的任务（按完成顺序，不阻塞）
            for future in as_completed(future_to_task):
                idx, segment_id = future_to_task[future]
                completed_count += 1
                
                # 计算进度百分比
                progress_pct = int((completed_count / total) * 100)
                progress_bar_length = int((completed_count / total) * 50)
                progress_bar = '█' * progress_bar_length + ' ' * (50 - progress_bar_length)
                
                try:
                    segment = future.result()
                    if segment is not None:
                        results[idx] = segment
                        if verbose:
                            # 显示进度条和详细信息
                            print(f"   [{completed_count}/{total}] {progress_bar} {progress_pct}% ✓ {segment_id} ({segment.total_duration:.2f}s, {len(segment.words)} words)")
                    else:
                        if verbose:
                            print(f"   [{completed_count}/{total}] {progress_bar} {progress_pct}% ❌ {segment_id} (failed)")
                except Exception as e:
                    if verbose:
                        print(f"   [{completed_count}/{total}] {progress_bar} {progress_pct}% ❌ {segment_id} (error: {e})")
                        import traceback
                        traceback.print_exc()
        
        # 按原始顺序返回结果
        segments = [results[i] for i in sorted(results.keys())]
        
        if verbose:
            # 完成时显示完整进度条
            print(f"   [{completed_count}/{total}] {'█' * 50} 100%")
            print(f"✅ Completed: {len(segments)}/{total} segments generated successfully")
        
        return segments
    
    def _generate_audio_safe(
        self,
        segment_id: str,
        text: str,
        language: str,
        ssml: Optional[str],
        idx: int,
    ) -> Optional[AudioSegment]:
        """
        安全地生成音频（用于并行处理，捕获所有异常）
        
        Args:
            segment_id: 片段ID
            text: 文本内容
            language: 语言代码
            ssml: 可选的SSML
            idx: 原始索引（用于排序）
        
        Returns:
            AudioSegment 或 None（如果失败）
        """
        try:
            return self.generate_audio(segment_id, text, language, ssml, verbose=False)
        except Exception as e:
            print(f"⚠️  Failed to generate audio for {segment_id}: {e}")
            return None
    
    def save_manifest(
        self,
        segments: List[AudioSegment],
        manifest_path: Optional[str] = None,
    ) -> str:
        """
        保存音频清单（包含所有时间戳信息）
        
        Args:
            segments: 音频片段列表
            manifest_path: 清单文件路径（默认：output_dir/audio_manifest.json）
        
        Returns:
            str: 清单文件路径
        """
        if manifest_path is None:
            manifest_path = self.output_dir / "audio_manifest.json"
        else:
            manifest_path = Path(manifest_path)
        
        manifest = {
            'version': '1.0',
            'total_segments': len(segments),
            'segments': [seg.to_dict() for seg in segments],
        }
        
        with open(manifest_path, 'w', encoding='utf-8') as f:
            json.dump(manifest, f, indent=2, ensure_ascii=False)
        
        print(f"\n📄 Audio manifest saved to: {manifest_path}")
        return str(manifest_path)
    
    @staticmethod
    def _get_audio_duration(audio_path: Path) -> float:
        """
        获取音频时长（秒）
        优先用 wave 模块读取 WAV 头（准确，无外部依赖），
        ffprobe 作为备选，最后才用文件大小估算。
        """
        # 方法1: 用 wave 模块读取 WAV 头（最可靠，Azure TTS 输出 24/48kHz）
        try:
            import wave
            with wave.open(str(audio_path), 'rb') as wf:
                frames = wf.getnframes()
                rate = wf.getframerate()
                if rate > 0 and frames >= 0:
                    return frames / float(rate)
        except Exception:
            pass

        # 方法2: ffprobe
        try:
            result = subprocess.run(
                [
                    'ffprobe', '-v', 'error',
                    '-show_entries', 'format=duration',
                    '-of', 'default=noprint_wrappers=1:nokey=1',
                    str(audio_path)
                ],
                capture_output=True,
                text=True,
                check=True,
                timeout=5,
            )
            return float(result.stdout.strip())
        except (subprocess.CalledProcessError, FileNotFoundError, ValueError, subprocess.TimeoutExpired):
            pass

        # 方法3: 文件大小估算（需知道采样率，Azure 多为 24/48kHz）
        # 48kHz 16-bit mono = 96000 bytes/s; 24kHz = 48000 bytes/s
        file_size = audio_path.stat().st_size
        bytes_per_sec = 96000.0  # Azure Neural TTS 常用 48kHz
        return file_size / bytes_per_sec


# 便捷函数
def generate_audio_from_config(
    config_path: str,
    output_dir: str = DEFAULT_AUDIO_OUTPUT_DIR,
    language: str = "en-US",
    audio_prefix: Optional[str] = None,
) -> Tuple[List[AudioSegment], str]:
    """
    从配置文件生成音频
    
    Args:
        config_path: 配置文件路径（JSON）
        output_dir: 输出目录
        language: 语言代码
        audio_prefix: 音频文件名前缀（用于区分不同配置的音频，避免覆盖）
    
    Returns:
        Tuple[List[AudioSegment], str]: (音频片段列表, 清单文件路径)
    """
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    # 提取所有场景的旁白
    narrations = []
    for scene in config.get('scenes', []):
        scene_id = scene['id']
        for idx, narr in enumerate(scene.get('narration', [])):
            # 如果提供了前缀，则在 segment_id 前加上前缀
            if audio_prefix:
                segment_id = f"{audio_prefix}_{scene_id}_narr{idx}"
            else:
                segment_id = f"{scene_id}_narr{idx}"
            narrations.append({
                'id': segment_id,
                'text': narr['text'],
                'ssml': narr.get('ssml'),
            })
    
    # 生成音频
    generator = TTSGenerator(output_dir=output_dir)
    segments = generator.generate_batch(narrations, language=language)
    manifest_path = generator.save_manifest(segments)
    
    return segments, manifest_path


if __name__ == "__main__":
    # 测试代码
    generator = TTSGenerator(output_dir="audio_test")
    
    test_segment = generator.generate_audio(
        segment_id="test_segment",
        text="Amazon leads with 574.8 billion dollars in revenue.",
        language="en-US",
    )
    
    print("\n🎯 Word Timestamps:")
    for word in test_segment.words:
        print(f"   {word.word:20s} [{word.start:.3f}s - {word.end:.3f}s]")

