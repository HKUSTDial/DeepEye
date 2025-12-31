"""NL2DV 模块 - 自然语言转数据视频

该模块提供从自然语言描述和 DataFrame 生成完整数据视频的完整流程。

主要包含两个子模块：
- config_generation: 自然语言 + DataFrame → 视频配置 JSON
- video_generation: 视频配置 JSON → 完整视频

快速开始：
    from deepeye.nodes.nl2dv import NL2DVNode
    from deepeye.nodes.io import NodeInput
    import pandas as pd
    
    # 创建节点并生成配置
    node = NL2DVNode(node_id="nl2dv1", config={...})
    outputs = node.run({
        "data": NodeInput(data={"dataframe": df}),
        "task": NodeInput(data={"description": "生成视频"})
    })
    config = outputs["config"].data
    
    # 使用 pipeline.py 生成完整视频
    # python -m deepeye.nodes.nl2dv.pipeline --query "..." --data data.csv
"""

from .config_generation.nl2dv import NL2DVNode, NL2DVConfig
from .config_generation.generator import SimpleConfigGenerator

__all__ = [
    "NL2DVNode",
    "NL2DVConfig",
    "SimpleConfigGenerator",
]

