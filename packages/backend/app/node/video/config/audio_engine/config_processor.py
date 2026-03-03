#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Config Processor - 配置文件处理器

核心功能：
1. 验证配置文件格式
2. 将简化配置扩展为完整配置
3. 处理默认值

这个模块让用户可以写极简的配置，系统自动补全细节
"""

import json
from pathlib import Path
from typing import Dict, Any, List
from copy import deepcopy


class ConfigProcessor:
    """配置文件处理器"""
    
    # 默认值
    DEFAULT_META = {
        "fps": 30,
        "width": 1280,
        "height": 720,
    }
    
    DEFAULT_SCENE_DURATION = 5.0  # 默认场景时长（秒）
    
    DEFAULT_ANIMATION_STYLES = {
        "entrance": {
            "effect": "fade_in",
            "duration": 1.0,
            "style": {"easing": "ease_out"},
        },
        "emphasis": {
            "effect": "highlight",
            "duration": 2.0,
            "style": {"glow": True, "intensity": 0.7},
        },
        "exit": {
            "effect": "fade_out",
            "duration": 0.8,
            "style": {"easing": "ease_in"},
        },
    }
    
    @classmethod
    def process(cls, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理配置文件（补全默认值）
        
        Args:
            config: 原始配置（可以很简化）
        
        Returns:
            Dict: 完整的配置
        """
        processed = deepcopy(config)
        
        # 补全 meta
        if 'meta' not in processed:
            processed['meta'] = {}
        processed['meta'] = {**cls.DEFAULT_META, **processed['meta']}
        
        # 处理场景
        if 'scenes' in processed:
            processed['scenes'] = [
                cls._process_scene(scene, idx)
                for idx, scene in enumerate(processed['scenes'])
            ]
        
        return processed
    
    @classmethod
    def _process_scene(cls, scene: Dict, scene_index: int) -> Dict:
        """处理单个场景"""
        processed = deepcopy(scene)
        
        # 补全场景 ID
        if 'id' not in processed:
            processed['id'] = f"scene_{scene_index + 1}"
        
        # 补全场景类型
        if 'type' not in processed:
            processed['type'] = 'chart'  # 默认为图表场景
        
        # 处理旁白
        if 'narration' in processed:
            processed['narration'] = [
                cls._process_narration(narr, idx)
                for idx, narr in enumerate(processed['narration'])
            ]
        
        # 处理动画
        if 'animations' in processed:
            processed['animations'] = [
                cls._process_animation(anim, idx)
                for idx, anim in enumerate(processed['animations'])
            ]
        
        return processed
    
    @classmethod
    def _process_narration(cls, narration: Dict, narr_index: int) -> Dict:
        """处理旁白配置"""
        processed = deepcopy(narration)
        
        # 旁白必须有 text 字段
        if 'text' not in processed:
            raise ValueError(f"Narration {narr_index} missing 'text' field")
        
        return processed
    
    @classmethod
    def _process_animation(cls, animation: Dict, anim_index: int) -> Dict:
        """处理动画配置（补全默认样式）"""
        processed = deepcopy(animation)
        
        # 补全动画类型
        if 'type' not in processed:
            processed['type'] = 'emphasis'
        
        # 补全动画效果和样式（如果没有指定）
        anim_type = processed['type']
        if anim_type in cls.DEFAULT_ANIMATION_STYLES:
            defaults = cls.DEFAULT_ANIMATION_STYLES[anim_type]
            
            if 'effect' not in processed:
                processed['effect'] = defaults['effect']
            
            if 'duration' not in processed:
                processed['duration'] = defaults['duration']
            
            if 'style' not in processed:
                processed['style'] = {}
            processed['style'] = {**defaults.get('style', {}), **processed['style']}
        
        return processed
    
    @classmethod
    def validate(cls, config: Dict[str, Any]) -> List[str]:
        """
        验证配置文件
        
        Returns:
            List[str]: 错误信息列表（空列表表示无错误）
        """
        errors = []
        
        # 检查必需字段
        if 'meta' not in config:
            errors.append("Missing 'meta' field")
        
        if 'scenes' not in config or not config['scenes']:
            errors.append("Missing or empty 'scenes' field")
        
        # 检查场景
        for idx, scene in enumerate(config.get('scenes', [])):
            if 'type' not in scene:
                errors.append(f"Scene {idx}: missing 'type' field")
            
            # 图表场景必须有 content 和 chart_type
            if scene.get('type') == 'chart':
                if 'content' not in scene:
                    errors.append(f"Scene {idx}: chart scene missing 'content' field")
                else:
                    content = scene.get('content', {})
                    if 'chart_type' not in content:
                        errors.append(f"Scene {idx}: chart scene missing 'chart_type' field in content")
        
        return errors
    
    @classmethod
    def load_and_process(cls, config_path: str) -> Dict[str, Any]:
        """
        加载并处理配置文件
        
        Args:
            config_path: 配置文件路径
        
        Returns:
            Dict: 处理后的配置
        """
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        # 验证
        errors = cls.validate(config)
        if errors:
            raise ValueError(f"Config validation failed:\n" + "\n".join(f"  - {e}" for e in errors))
        
        # 处理
        return cls.process(config)
    
    @classmethod
    def create_minimal_example(cls) -> Dict[str, Any]:
        """
        创建一个最小示例配置（用于文档）
        
        Returns:
            Dict: 最小配置示例
        """
        return {
            "meta": {
                "title": "My Data Story",
            },
            "scenes": [
                {
                    "type": "opening",
                    "content": {
                        "title": "Data Insights 2024",
                        "subtitle": "A Data-Driven Story",
                    },
                    "narration": [
                        {"text": "Welcome to our data story"}
                    ],
                },
                {
                    "type": "chart",
                    "content": {
                        "chart_type": "bar_chart",
                        "title": "Revenue by Company",
                        "data": [
                            {"company": "A", "revenue": 100},
                            {"company": "B", "revenue": 150},
                        ],
                        "data_binding": {
                            "x_axis": {"field": "company"},
                            "y_axis": {"field": "revenue"},
                        },
                    },
                    "narration": [
                        {
                            "text": "Company B leads with 150 million",
                            "linked_data": {
                                "data_filter": {"company": "B"}
                            }
                        }
                    ],
                    "animations": [
                        {
                            "type": "entrance",
                            "trigger_narration": 0,  # 🎯 关键：引用旁白索引，自动同步时间
                        },
                        {
                            "type": "emphasis",
                            "trigger_narration": 0,
                            "target_data": {
                                "data_filter": {"company": "B"}
                            },
                        }
                    ],
                },
                {
                    "type": "closing",
                    "content": {
                        "message": "Thank you for watching!",
                    },
                    "narration": [
                        {"text": "Thanks for your attention"}
                    ],
                },
            ],
        }


def save_minimal_example(output_path: str = "configs/minimal_auto_example.json"):
    """保存最小示例配置"""
    example = ConfigProcessor.create_minimal_example()
    
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(example, f, indent=2, ensure_ascii=False)
    
    print(f"✅ Minimal example saved to: {output_path}")
    print("\n📝 Key features of this config:")
    print("   - No manual time_start/time_end needed")
    print("   - Animations use 'trigger_narration' to auto-sync")
    print("   - TTS will generate audio + word timestamps")
    print("   - TimeAligner will calculate all timings automatically")
    
    return str(output_path)


if __name__ == "__main__":
    # 测试：生成最小示例
    save_minimal_example()
    
    # 测试：处理配置
    processor = ConfigProcessor()
    minimal = processor.create_minimal_example()
    processed = processor.process(minimal)
    
    print("\n✅ Processed config:")
    print(json.dumps(processed, indent=2))

