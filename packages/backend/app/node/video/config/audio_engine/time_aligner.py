#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Time Aligner - 自动时间对齐模块

核心功能：
1. 根据 TTS word timestamps 自动计算旁白的 time_start 和 time_end
2. 将动画时间与旁白时间同步（narration-animation interplay）
3. 处理场景时间累积

参考：Data Player 论文 Section 4.4 - Animation Design as CSP
"""

import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from copy import deepcopy

from .tts_generator import AudioSegment, WordTimestamp
from .constants import DEFAULT_ANIMATION_OFFSET, DEFAULT_ANIMATION_PADDING


@dataclass
class AlignedConfig:
    """对齐后的配置"""
    config: Dict[str, Any]          # 完整配置
    total_duration: float           # 总时长
    audio_files: List[str]          # 音频文件列表


class TimeAligner:
    """时间自动对齐器"""
    
    def __init__(
        self,
        animation_offset: float = DEFAULT_ANIMATION_OFFSET,
        animation_padding: float = DEFAULT_ANIMATION_PADDING,
    ):
        """
        初始化时间对齐器
        
        Args:
            animation_offset: 动画相对于旁白的偏移（秒，负数表示提前）
            animation_padding: 动画在旁白结束后的额外持续时间（秒）
        """
        self.animation_offset = animation_offset
        self.animation_padding = animation_padding
    
    def align_config(
        self,
        config: Dict[str, Any],
        audio_segments: List[AudioSegment],
    ) -> AlignedConfig:
        """
        将音频时间戳应用到配置文件
        
        Args:
            config: 原始配置（可以没有时间戳）
            audio_segments: TTS 生成的音频片段（包含 word timestamps）
        
        Returns:
            AlignedConfig: 对齐后的配置
        """
        print("⏱️  Aligning timeline...")
        
        # 深拷贝配置，避免修改原始数据
        aligned_config = deepcopy(config)
        
        # 创建音频片段索引（按 segment_id）
        audio_index = {seg.segment_id: seg for seg in audio_segments}
        
        # 累积时间（用于计算场景的绝对时间）
        current_time = 0.0
        audio_files = []
        
        # 遍历所有场景
        for scene in aligned_config.get('scenes', []):
            scene_id = scene['id']
            scene_start_time = current_time
            
            # 对齐场景内的旁白
            scene_duration = self._align_scene_narrations(
                scene=scene,
                scene_id=scene_id,
                scene_start_time=scene_start_time,
                audio_index=audio_index,
            )
            
            # 对齐场景内的动画
            self._align_scene_animations(
                scene=scene,
                scene_start_time=scene_start_time,
                audio_index=audio_index,
            )
            
            # 更新场景时间范围
            scene_end_time = scene_start_time + scene_duration
            scene['time_range'] = [
                round(scene_start_time, 3),
                round(scene_end_time, 3),
            ]
            
            # 累积时间
            current_time = scene_end_time
            
            # 收集音频文件
            for narr_idx in range(len(scene.get('narration', []))):
                segment_id_base = f"{scene_id}_narr{narr_idx}"
                # 尝试直接匹配（不带前缀的情况）
                segment_id = segment_id_base
                if segment_id not in audio_index:
                    # 如果直接匹配失败，尝试匹配带前缀的 segment_id
                    matching_key = None
                    for key in audio_index.keys():
                        if key.endswith(f"_{segment_id_base}") or key == segment_id_base:
                            matching_key = key
                            break
                    if matching_key:
                        segment_id = matching_key
                
                if segment_id in audio_index:
                    audio_files.append(audio_index[segment_id].audio_file)
            
            print(f"   ✓ {scene_id}: [{scene_start_time:.2f}s - {scene_end_time:.2f}s] ({scene_duration:.2f}s)")
        
        # 更新视频总时长
        aligned_config['meta']['video_duration'] = round(current_time, 2)
        
        print(f"\n✅ Total video duration: {current_time:.2f}s")
        
        return AlignedConfig(
            config=aligned_config,
            total_duration=current_time,
            audio_files=audio_files,
        )
    
    def _align_scene_narrations(
        self,
        scene: Dict,
        scene_id: str,
        scene_start_time: float,
        audio_index: Dict[str, AudioSegment],
    ) -> float:
        """
        对齐场景内的旁白时间
        
        Returns:
            float: 场景总时长
        """
        narrations = scene.get('narration', [])
        if not narrations:
            # 如果没有旁白，使用默认时长
            return scene.get('time_range', [0, 3.0])[1] - scene.get('time_range', [0, 3.0])[0]
        
        # 累积场景内时间
        scene_time = 0.0
        
        for idx, narr in enumerate(narrations):
            # 构建 segment_id（可能带前缀，也可能不带）
            segment_id_base = f"{scene_id}_narr{idx}"
            
            # 尝试直接匹配（不带前缀的情况）
            segment_id = segment_id_base
            if segment_id not in audio_index:
                # 如果直接匹配失败，尝试匹配带前缀的 segment_id
                # 查找 audio_index 中所有以 segment_id_base 结尾的键
                matching_key = None
                for key in audio_index.keys():
                    if key.endswith(f"_{segment_id_base}") or key == segment_id_base:
                        matching_key = key
                        break
                
                if matching_key:
                    segment_id = matching_key
                else:
                    # 没有找到匹配的音频文件，使用默认时长
                    print(f"   ⚠️  Warning: No audio found for {segment_id_base}, using default duration")
                    # 使用已有时间或默认时长
                    if 'time_start' in narr and 'time_end' in narr:
                        duration = narr['time_end'] - narr['time_start']
                    else:
                        duration = 3.0  # 默认 3 秒
                    
                    narr['time_start'] = round(scene_start_time + scene_time, 3)
                    narr['time_end'] = round(scene_start_time + scene_time + duration, 3)
                    scene_time += duration
                    continue
            
            # 从音频片段获取时间信息
            audio_seg = audio_index[segment_id]
            
            # 设置旁白的绝对时间
            narr['time_start'] = round(scene_start_time + scene_time, 3)
            narr['time_end'] = round(scene_start_time + scene_time + audio_seg.total_duration, 3)
            
            # 添加音频文件引用
            narr['audio_file'] = audio_seg.audio_file
            
            # 如果有 linked_data，尝试匹配关键词并找到精确时间
            if 'linked_data' in narr and narr['linked_data']:
                narr['_word_timestamps'] = self._extract_keyword_timestamps(
                    audio_seg=audio_seg,
                    linked_data=narr['linked_data'],
                )
            
            # 累积时间
            scene_time += audio_seg.total_duration
        
        # 直接返回音频的实际时长，不使用最小时长限制
        # 视频时长应该完全基于音频的实际时长
        return scene_time
    
    def _align_scene_animations(
        self,
        scene: Dict,
        scene_start_time: float,
        audio_index: Optional[Dict[str, AudioSegment]] = None,
    ):
        """
        对齐场景内的动画时间
        
        策略：
        1. 如果动画有 `trigger_narration` 字段，使用对应旁白的时间
        2. 对于 emphasis 动画，尝试使用词级别时间戳精确对齐
        3. 如果动画已有绝对时间，保持不变
        4. 如果动画有相对时间（相对于场景），转换为绝对时间
        
        改进：对于同一 narration 的多个动画，按顺序处理，避免重复使用相同的时间戳
        """
        animations = scene.get('animations', [])
        narrations = scene.get('narration', [])
        scene_id = scene.get('id', 'unknown')
        
        # 按 trigger_narration 分组处理动画，确保同一 narration 的动画按顺序处理
        animations_by_narration = {}
        other_animations = []
        
        for anim in animations:
            if 'trigger_narration' in anim:
                narr_index = anim['trigger_narration']
                if narr_index not in animations_by_narration:
                    animations_by_narration[narr_index] = []
                animations_by_narration[narr_index].append(anim)
            else:
                other_animations.append(anim)
        
        # 处理按 narration 分组的动画
        for narr_index, anims in animations_by_narration.items():
            # 验证 trigger_narration 索引是否有效
            if narr_index < 0 or narr_index >= len(narrations):
                for anim in anims:
                    print(f"   ⚠️  Warning: Animation '{anim.get('id', 'unknown')}' has invalid trigger_narration: {narr_index} (only {len(narrations)} narrations exist, indices 0-{len(narrations)-1})")
                continue
            
            narr = narrations[narr_index]
            
            # 记录已使用的时间戳位置（用于避免重复匹配）
            used_word_indices = set()
            max_used_index = -1  # 记录已使用的最大索引
            
            # 对于同一 narration 的多个 emphasis 动画，按顺序处理
            for anim in anims:
                # 验证 emphasis 动画的 data_filter 是否与 narration 文本匹配
                if anim.get('type') == 'emphasis' and anim.get('target_data', {}).get('data_filter'):
                    data_filter = anim['target_data']['data_filter']
                    keyword = self._extract_primary_keyword(data_filter)
                    narration_text = narr.get('text', '').lower()
                    
                    # 检查关键词是否在 narration 文本中（简单验证）
                    if keyword and keyword.lower() not in narration_text:
                        print(f"   ⚠️  Warning: Animation '{anim.get('id', 'unknown')}' targets '{keyword}' but Narration {narr_index} says: \"{narr.get('text', '')[:80]}...\"")
                        print(f"      This may cause incorrect highlighting. Please verify the animation configuration.")
                
                # 默认继承旁白的时间范围
                anim['time_start'] = narr['time_start'] + self.animation_offset
                
                # 计算持续时间
                if 'duration' not in anim:
                    narr_duration = narr['time_end'] - narr['time_start']
                    anim['duration'] = narr_duration + self.animation_padding
                
                # 🎯 词级别时间对齐（新增）：对于 emphasis 动画，尝试匹配具体词
                if (anim.get('type') == 'emphasis' and 
                    anim.get('target_data', {}).get('data_filter') and
                    audio_index):
                    
                    # 获取音频片段（支持带前缀的 segment_id）
                    segment_id_base = f"{scene_id}_narr{narr_index}"
                    segment_id = segment_id_base
                    if segment_id not in audio_index:
                        # 如果直接匹配失败，尝试匹配带前缀的 segment_id
                        matching_key = None
                        for key in audio_index.keys():
                            if key.endswith(f"_{segment_id_base}") or key == segment_id_base:
                                matching_key = key
                                break
                        if matching_key:
                            segment_id = matching_key
                    
                    if segment_id in audio_index:
                        audio_seg = audio_index[segment_id]
                        
                        # 提取实体名称作为关键词
                        data_filter = anim['target_data']['data_filter']
                        keyword = self._extract_primary_keyword(data_filter)
                        
                        if keyword and audio_seg.words:
                            # 在词时间戳中查找关键词（从已使用的位置之后开始查找）
                            word_time = self._find_keyword_timestamp(
                                audio_seg.words, 
                                keyword,
                                narr['time_start'],
                                start_from_index=max_used_index + 1  # 从已使用的最大索引之后开始
                            )
                            
                            if word_time:
                                # 使用词的精确时间
                                anim['time_start'] = word_time['start']
                                # 持续时间从词开始到旁白结束
                                anim['duration'] = narr['time_end'] - word_time['start']
                                
                                # 记录已使用的词索引
                                if 'word_index' in word_time:
                                    used_word_indices.add(word_time['word_index'])
                                    max_used_index = max(max_used_index, word_time['word_index'])
                                
                                # 添加调试信息（可选）
                                if not anim.get('_debug_info'):
                                    anim['_debug_info'] = {}
                                anim['_debug_info']['word_aligned'] = True
                                anim['_debug_info']['keyword'] = keyword
                                anim['_debug_info']['word_time'] = word_time['start']
                            else:
                                # 关键词在 narration 文本中但不在 word timestamps 中（可能是部分匹配）
                                print(f"   ℹ️  Info: Keyword '{keyword}' not found in word timestamps for Narration {narr_index}, using narration start time")
        
        # 处理其他动画（没有 trigger_narration 的）
        for anim in other_animations:
            # 如果动画时间是相对于场景的，转换为绝对时间
            if 'time_start' in anim:
                # 检查是否已经是绝对时间（大于场景开始时间）
                if anim['time_start'] < scene_start_time:
                    # 假设是相对时间，转换为绝对时间
                    anim['time_start'] = scene_start_time + anim['time_start']
    
    def _extract_primary_keyword(self, data_filter: Dict) -> Optional[str]:
        """从 data_filter 中提取主要关键词"""
        for key, value in data_filter.items():
            if isinstance(value, str):
                return value
            elif isinstance(value, list) and len(value) > 0:
                return str(value[0])
        return None
    
    def _find_keyword_timestamp(
        self, 
        words: List[WordTimestamp], 
        keyword: str,
        base_time: float,
        start_from_index: int = 0
    ) -> Optional[Dict]:
        """
        在词时间戳列表中查找关键词
        
        Args:
            words: 词时间戳列表
            keyword: 要查找的关键词（如 "Amazon" 或 "App B"）
            base_time: 旁白的开始时间（用于转换为绝对时间）
            start_from_index: 从哪个索引开始查找（用于避免重复匹配同一 narration 中的多个关键词）
            
        Returns:
            包含 'start', 'end', 'word_index' 的字典，或 None
        """
        keyword_lower = keyword.lower().strip()
        keyword_parts = keyword_lower.split()  # 支持多词关键词，如 "App B" -> ["app", "b"]
        
        # 策略1: 优先完全匹配（精确匹配）
        for i in range(start_from_index, len(words)):
            word_ts = words[i]
            word_lower = word_ts.word.lower()
            
            # 完全匹配（忽略大小写）
            if keyword_lower == word_lower:
                return {
                    'word': word_ts.word,
                    'start': base_time + word_ts.start,
                    'end': base_time + word_ts.end,
                    'word_index': i,
                }
        
        # 策略2: 多词关键词匹配（如 "App B" 匹配连续的 "App" 和 "B"）
        if len(keyword_parts) > 1:
            for i in range(start_from_index, len(words) - len(keyword_parts) + 1):
                # 检查连续的词是否匹配关键词的各个部分
                match = True
                for j, part in enumerate(keyword_parts):
                    if i + j >= len(words):
                        match = False
                        break
                    word_lower = words[i + j].word.lower()
                    # 部分匹配：关键词部分在词中，或词在关键词部分中
                    if part not in word_lower and word_lower not in part:
                        match = False
                        break
                
                if match:
                    # 返回第一个词的开始时间和最后一个词的结束时间
                    first_word = words[i]
                    last_word = words[i + len(keyword_parts) - 1]
                    return {
                        'word': ' '.join([words[i + j].word for j in range(len(keyword_parts))]),
                        'start': base_time + first_word.start,
                        'end': base_time + last_word.end,
                        'word_index': i,
                    }
        
        # 策略3: 单词部分匹配（例如 "Amazon" 可以匹配 "Amazon's"）
        for i in range(start_from_index, len(words)):
            word_ts = words[i]
            word_lower = word_ts.word.lower()
            # 支持部分匹配（例如 "Amazon" 可以匹配 "Amazon's"）
            if keyword_lower in word_lower or word_lower in keyword_lower:
                return {
                    'word': word_ts.word,
                    'start': base_time + word_ts.start,
                    'end': base_time + word_ts.end,
                    'word_index': i,
                }
        
        return None
    
    def _extract_keyword_timestamps(
        self,
        audio_seg: AudioSegment,
        linked_data: Dict,
    ) -> List[Dict]:
        """
        从 word timestamps 中提取关键词的时间
        
        例如：linked_data = {"company": "Amazon"}
        提取 "Amazon" 这个词的时间戳
        """
        keywords = []
        
        # 从 data_filter 提取值作为关键词
        data_filter = linked_data.get('data_filter', {})
        if data_filter:
            for key, value in data_filter.items():
                if isinstance(value, str):
                    keywords.append(value.lower())
                elif isinstance(value, list):
                    keywords.extend([str(v).lower() for v in value])
        
        # 在 word timestamps 中查找关键词
        keyword_times = []
        for word_ts in audio_seg.words:
            word_lower = word_ts.word.lower()
            for keyword in keywords:
                if keyword in word_lower or word_lower in keyword:
                    keyword_times.append({
                        'word': word_ts.word,
                        'start': word_ts.start,
                        'end': word_ts.end,
                    })
        
        return keyword_times
    
    def save_aligned_config(
        self,
        aligned_config: AlignedConfig,
        output_path: str,
    ) -> str:
        """
        保存对齐后的配置
        
        Args:
            aligned_config: 对齐后的配置
            output_path: 输出路径
        
        Returns:
            str: 输出文件路径
        """
        output_path = Path(output_path)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(aligned_config.config, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 Aligned config saved to: {output_path}")
        return str(output_path)


def align_config_with_audio(
    config_path: str,
    audio_manifest_path: str,
    output_path: Optional[str] = None,
) -> AlignedConfig:
    """
    便捷函数：从文件加载并对齐配置
    
    Args:
        config_path: 原始配置文件路径
        audio_manifest_path: 音频清单文件路径
        output_path: 输出配置文件路径（可选）
    
    Returns:
        AlignedConfig: 对齐后的配置
    """
    # 加载配置
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    # 加载音频清单
    with open(audio_manifest_path, 'r', encoding='utf-8') as f:
        manifest = json.load(f)
    
    # 重建 AudioSegment 对象
    from .tts_generator import AudioSegment, WordTimestamp
    
    audio_segments = []
    for seg_data in manifest['segments']:
        words = [WordTimestamp(**w) for w in seg_data['words']]
        segment = AudioSegment(
            segment_id=seg_data['segment_id'],
            text=seg_data['text'],
            audio_file=seg_data['audio_file'],
            total_duration=seg_data['total_duration'],
            words=words,
            language=seg_data.get('language', 'en-US'),
        )
        audio_segments.append(segment)
    
    # 对齐
    aligner = TimeAligner()
    aligned = aligner.align_config(config, audio_segments)
    
    # 保存（如果指定了输出路径）
    if output_path:
        aligner.save_aligned_config(aligned, output_path)
    
    return aligned


if __name__ == "__main__":
    # 测试代码
    test_config = {
        "meta": {"fps": 30, "width": 1280, "height": 720},
        "scenes": [
            {
                "id": "scene1",
                "type": "chart",
                "narration": [
                    {"text": "Amazon leads with 574.8 billion dollars"},
                ],
                "animations": [
                    {
                        "type": "emphasis",
                        "trigger_narration": 0,
                        "effect": "highlight",
                    }
                ],
            }
        ],
    }
    
    # 创建模拟音频片段
    from .tts_generator import AudioSegment, WordTimestamp
    
    test_audio = AudioSegment(
        segment_id="scene1_narr0",
        text="Amazon leads with 574.8 billion dollars",
        audio_file="audio/scene1_narr0.wav",
        total_duration=3.5,
        words=[
            WordTimestamp("Amazon", 0.0, 0.4, 0.4),
            WordTimestamp("leads", 0.4, 0.8, 0.4),
            WordTimestamp("with", 0.8, 1.0, 0.2),
            WordTimestamp("574.8", 1.0, 1.6, 0.6),
            WordTimestamp("billion", 1.6, 2.2, 0.6),
            WordTimestamp("dollars", 2.2, 3.5, 1.3),
        ],
    )
    
    aligner = TimeAligner()
    result = aligner.align_config(test_config, [test_audio])
    
    print("\n✅ Aligned Config:")
    print(json.dumps(result.config, indent=2))

