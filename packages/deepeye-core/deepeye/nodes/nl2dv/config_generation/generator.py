"""
配置生成器 - 适配 DeepEye LLMClient

三阶段生成：
1. Data Analyst: 提取洞察
2. Scene Designer: 生成完整配置（不含时间）
3. Animation Coordinator: 添加动画（可选）
"""

import json
from typing import Dict, List, Any, Optional

from deepeye.llm import LLMClient, Message

from .prompts import (
    format_data_analyst_prompt,
    format_scene_designer_prompt,
    format_animation_coordinator_prompt
)


def _parse_json_response(response_text: str) -> Dict:
    """解析 LLM 响应中的 JSON
    
    Args:
        response_text: LLM 返回的文本
        
    Returns:
        解析后的 JSON 字典
        
    Raises:
        ValueError: 无法解析 JSON
    """
    # 尝试直接解析
    try:
        return json.loads(response_text)
    except json.JSONDecodeError:
        pass
    
    # 尝试提取 ```json ... ``` 中的内容
    if "```json" in response_text:
        start = response_text.find("```json") + 7
        end = response_text.find("```", start)
        if end > start:
            json_str = response_text[start:end].strip()
            try:
                return json.loads(json_str)
            except json.JSONDecodeError:
                pass
    
    # 尝试提取 ``` ... ``` 中的内容
    if "```" in response_text:
        start = response_text.find("```") + 3
        end = response_text.find("```", start)
        if end > start:
            json_str = response_text[start:end].strip()
            # 移除可能的语言标识符（如 ```json）
            if json_str.startswith("json"):
                json_str = json_str[4:].strip()
            try:
                return json.loads(json_str)
            except json.JSONDecodeError:
                pass
    
    # 尝试查找 JSON 对象（从第一个 { 到最后一个 }）
    start = response_text.find("{")
    end = response_text.rfind("}")
    if start >= 0 and end > start:
        json_str = response_text[start:end+1]
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            pass
    
    raise ValueError(f"无法解析JSON响应:\n{response_text[:500]}")


class SimpleConfigGenerator:
    """简化版配置生成器
    
    使用 DeepEye 的 LLMClient 进行多阶段配置生成。
    """
    
    def __init__(
        self, 
        llm_client: LLMClient,
        model: str = "gpt-4o"
    ):
        """初始化生成器
        
        Args:
            llm_client: DeepEye LLM 客户端
            model: 使用的模型名称
        """
        self.llm_client = llm_client
        self.model = model
    
    def generate(
        self,
        query: str,
        data: List[Dict],
        language: str = "English",
        verbose: bool = True,
        skip_animations: bool = False
    ) -> Dict[str, Any]:
        """
        生成视频配置
        
        Args:
            query: 用户查询
            data: 原始数据（List[Dict]）
            language: 输出语言 (English, Chinese, etc.)
            verbose: 是否打印详细信息
            skip_animations: 是否跳过动画生成（默认False）
        
        Returns:
            完整的视频配置（不含时间字段，但包含动画）
        """
        if verbose:
            print("\n" + "="*60)
            print("🎬 开始生成视频配置")
            print("="*60)
        
        # 阶段1: 数据分析
        if verbose:
            print("\n📊 阶段1: 数据分析...")
        
        insights = self._analyze_data(query, data, language, verbose)
        
        if verbose:
            print(f"✅ 提取了 {len(insights)} 个洞察")
            for i, insight in enumerate(insights, 1):
                print(f"   {i}. [{insight['type']}] {insight['content']}")
        
        # 阶段2: 场景设计
        if verbose:
            print("\n🎨 阶段2: 场景设计...")
        
        config = self._design_scenes(query, insights, data, language, verbose)
        
        if verbose:
            print(f"✅ 生成了 {len(config['scenes'])} 个场景")
            print(f"   标题: {config['meta']['title']}")
        
        # 阶段3: 动画编排（可选）
        if not skip_animations:
            if verbose:
                print("\n🎭 阶段3: 动画编排...")
            
            config = self._add_animations(config, verbose)
            
            if verbose:
                total_animations = sum(
                    len(scene.get("animations", [])) 
                    for scene in config["scenes"]
                )
                print(f"✅ 添加了 {total_animations} 个动画")
        
        return config
    
    def _analyze_data(self, query: str, data: List[Dict], language: str, verbose: bool) -> List[Dict]:
        """阶段1: 数据分析"""
        prompt = format_data_analyst_prompt(query, data, language)
        
        try:
            messages = [Message(role="user", content=prompt)]
            response = self.llm_client.generate(
                messages,
                model=self.model,
                temperature=0.7
            )
            
            response_dict = _parse_json_response(response.content)
            insights = response_dict.get("insights", [])
            
            if not insights:
                raise ValueError("未能提取到洞察")
            
            return insights
        
        except Exception as e:
            if verbose:
                print(f"⚠️  数据分析失败: {e}")
                print("使用默认洞察...")
            
            # 返回一个默认洞察
            return [{
                "type": "comparison",
                "content": f"分析数据集中的 {len(data)} 条记录",
                "importance": 0.8
            }]
    
    def _design_scenes(
        self,
        query: str,
        insights: List[Dict],
        data: List[Dict],
        language: str,
        verbose: bool
    ) -> Dict[str, Any]:
        """阶段2: 场景设计"""
        prompt = format_scene_designer_prompt(query, insights, data, language)
        
        try:
            messages = [Message(role="user", content=prompt)]
            response = self.llm_client.generate(
                messages,
                model=self.model,
                temperature=0.7,
                max_tokens=4000
            )
            
            config = _parse_json_response(response.content)
            
            # 验证配置
            if "meta" not in config or "scenes" not in config:
                raise ValueError("配置缺少必要字段")
            
            # 确保没有时间字段（清理）
            config = self._clean_time_fields(config)
            
            return config
        
        except Exception as e:
            if verbose:
                print(f"⚠️  场景设计失败: {e}")
                print("使用默认配置...")
            
            # 返回一个最简配置
            return self._create_fallback_config(query, data)
    
    def _add_animations(self, config: Dict, verbose: bool) -> Dict:
        """阶段3: 添加动画"""
        prompt = format_animation_coordinator_prompt(config)
        
        try:
            messages = [Message(role="user", content=prompt)]
            response = self.llm_client.generate(
                messages,
                model=self.model,
                temperature=0.6,  # 降低温度，保证一致性
                max_tokens=5000
            )
            
            config_with_animations = _parse_json_response(response.content)
            
            # 验证配置结构
            if "scenes" not in config_with_animations:
                raise ValueError("动画配置缺少scenes字段")
            
            # 确保没有手动设置的时间字段（动画中）
            config_with_animations = self._clean_animation_time_fields(config_with_animations)
            
            return config_with_animations
        
        except Exception as e:
            if verbose:
                print(f"⚠️  动画编排失败: {e}")
                print("使用无动画配置...")
            
            # 返回原配置（无动画）
            return config
    
    def _clean_time_fields(self, config: Dict) -> Dict:
        """清理配置中的时间字段"""
        # 移除顶层的 video_duration
        config.get("meta", {}).pop("video_duration", None)
        
        # 移除场景的时间字段
        for scene in config.get("scenes", []):
            scene.pop("time_range", None)
            
            # 移除旁白的时间字段
            for narr in scene.get("narration", []):
                narr.pop("time_start", None)
                narr.pop("time_end", None)
                narr.pop("audio_file", None)
        
        return config
    
    def _clean_animation_time_fields(self, config: Dict) -> Dict:
        """清理动画中手动设置的时间字段"""
        for scene in config.get("scenes", []):
            for anim in scene.get("animations", []):
                # 移除手动设置的时间（应该由 trigger_narration 驱动）
                anim.pop("time_start", None)
                # duration 可以保留（作为覆盖）
        
        return config
    
    def _create_fallback_config(self, query: str, data: List[Dict]) -> Dict:
        """创建兜底配置"""
        # 尝试猜测字段
        if not data:
            raise ValueError("数据为空")
        
        sample = data[0]
        fields = list(sample.keys())
        
        # 猜测 x 和 y 字段
        x_field = fields[0]
        y_field = fields[1] if len(fields) > 1 else fields[0]
        
        return {
            "meta": {
                "title": query or "数据分析",
                "fps": 30,
                "width": 1280,
                "height": 720
            },
            "scenes": [
                {
                    "id": "scene_opening",
                    "type": "opening",
                    "content": {
                        "title": query or "数据分析",
                        "subtitle": "基于数据的洞察"
                    },
                    "narration": [
                        {"text": "让我们一起分析这些数据"}
                    ]
                },
                {
                    "id": "scene_chart_1",
                    "type": "chart",
                    "content": {
                        "chart_type": "bar_chart",
                        "title": "数据可视化",
                        "data": data[:20],  # 限制数据量
                        "data_binding": {
                            "x_axis": {"field": x_field, "label": x_field},
                            "y_axis": {"field": y_field, "label": y_field}
                        },
                        "style": {
                            "bar_color": "#5b8ff9",
                            "highlight_color": "#ff6b6b",
                            "background_color": "#0f1419",
                            "container_background": "#0f1419",
                            "text_color": "#e8eaed",
                            "grid_color": "#555555",
                            "axis_color": "#888888"
                        },
                        "layout": {
                            "margin": {"top": 80, "right": 60, "bottom": 100, "left": 100},
                            "chart_area": {"width": 1120, "height": 540}
                        }
                    },
                    "narration": [
                        {"text": "这是我们的数据可视化"}
                    ]
                },
                {
                    "id": "scene_closing",
                    "type": "closing",
                    "content": {
                        "title": "感谢观看"
                    },
                    "narration": [
                        {"text": "以上是我们的分析"}
                    ]
                }
            ]
        }

