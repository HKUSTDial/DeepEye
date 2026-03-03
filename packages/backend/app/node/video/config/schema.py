"""
配置结构定义 - 简化版
生成不包含时间字段的配置，交由 audio_engine 自动对齐
"""

# 支持的图表类型
CHART_TYPES = ["bar_chart", "line_chart", "pie_chart", "scatter_chart", "heatmap"]

# 支持的场景类型
SCENE_TYPES = [
    "opening",
    "chart", 
    "stat_cards",
    "closing"
]

# 洞察类型
INSIGHT_TYPES = [
    "trend",              # 趋势变化
    "comparison",         # 对比差异
    "find_extremum",      # 找极值
    "outlier",            # 异常值
    "correlation",        # 相关性
    "part_to_whole",      # 占比关系
    "distribution",       # 分布特征
    "change_over_time",   # 时序变化
    "magnitude"           # 数值大小
]


# 简化的配置 Schema（不包含时间、动画等字段）
SIMPLE_CONFIG_SCHEMA = {
    "type": "object",
    "required": ["meta", "scenes"],
    "properties": {
        "meta": {
            "type": "object",
            "required": ["title", "fps", "width", "height"],
            "properties": {
                "title": {"type": "string", "description": "视频标题"},
                "fps": {"type": "integer", "default": 30},
                "width": {"type": "integer", "default": 1280},
                "height": {"type": "integer", "default": 720}
            }
        },
        "scenes": {
            "type": "array",
            "description": "场景列表，不需要包含时间字段",
            "items": {
                "type": "object",
                "required": ["id", "type", "content"],
                "properties": {
                    "id": {"type": "string", "description": "场景ID，如 scene_opening, scene_chart_1"},
                    "type": {"type": "string", "enum": SCENE_TYPES},
                    "content": {
                        "type": "object",
                        "description": "场景内容，根据type不同而不同"
                    },
                    "narration": {
                        "type": "array",
                        "description": "旁白列表，只需包含文本，不需要时间",
                        "items": {
                            "type": "object",
                            "required": ["text"],
                            "properties": {
                                "text": {"type": "string", "description": "旁白文本"}
                            }
                        }
                    }
                }
            }
        }
    }
}


def get_scene_content_schema(scene_type: str) -> dict:
    """获取不同场景类型的 content 结构"""
    
    if scene_type == "opening":
        return {
            "title": "string - 主标题",
            "subtitle": "string - 副标题（可选）"
        }
    
    elif scene_type == "chart":
        return {
            "chart_type": "string - 图表类型：bar_chart/line_chart/pie_chart/scatter_chart/heatmap",
            "title": "string - 图表标题",
            "data": "array - 数据数组",
            "data_binding": "object - 数据绑定配置，根据图表类型不同：\n" +
                           "  - bar_chart/line_chart/scatter_chart: {x_axis: {field, label}, y_axis: {field, label}}\n" +
                           "  - pie_chart: {label: {field, label}, value: {field, label}}\n" +
                           "  - heatmap: {x_axis: {field, label}, y_axis: {field, label}, value: {field, label}}",
            "color_scheme": "string - 配色方案（可选）：blue/green/purple/orange/red"
        }
    
    elif scene_type == "stat_cards":
        return {
            "title": "string - 卡片组标题",
            "cards": [
                {
                    "label": "string - 指标名称",
                    "value": "number/string - 指标值",
                    "unit": "string - 单位（可选）"
                }
            ]
        }
    
    elif scene_type == "closing":
        return {
            "title": "string - 结束语",
            "subtitle": "string - 副标题（可选）"
        }
    
    return {}


# 示例配置（供参考）
EXAMPLE_CONFIG = {
    "meta": {
        "title": "2023年科技公司收入分析",
        "fps": 30,
        "width": 1280,
        "height": 720
    },
    "scenes": [
        {
            "id": "scene_opening",
            "type": "opening",
            "content": {
                "title": "2023年科技公司收入分析",
                "subtitle": "数据驱动的洞察"
            },
            "narration": [
                {
                    "text": "让我们一起分析2023年主要科技公司的收入表现"
                }
            ]
        },
        {
            "id": "scene_chart_1",
            "type": "chart",
            "content": {
                "chart_type": "bar_chart",
                "title": "各公司收入对比",
                "data": [
                    {"company": "Apple", "revenue": 383.3},
                    {"company": "Microsoft", "revenue": 211.9},
                    {"company": "Alphabet", "revenue": 307.4}
                ],
                "data_binding": {
                    "x_axis": {"field": "company", "label": "Company"},
                    "y_axis": {"field": "revenue", "label": "Revenue (Billion $)"}
                }
            },
            "narration": [
                {
                    "text": "Apple以383.3亿美元的收入领跑科技行业"
                },
                {
                    "text": "Microsoft和Alphabet分别位列第二和第三"
                }
            ]
        },
        {
            "id": "scene_closing",
            "type": "closing",
            "content": {
                "title": "感谢观看",
                "subtitle": "数据来源：公开财报"
            },
            "narration": [
                {
                    "text": "以上是我们的分析，感谢观看"
                }
            ]
        }
    ]
}
