# NL2DV 模块 - 自然语言转数据视频

NL2DV（Natural Language to Data Video）模块提供从自然语言描述和 DataFrame 生成完整数据视频的端到端解决方案。

## 📋 目录

- [功能概述](#功能概述)
- [架构说明](#架构说明)
- [快速开始](#快速开始)
- [完整工作流程](#完整工作流程)
- [模块说明](#模块说明)
- [使用示例](#使用示例)
- [相关文档](#相关文档)

## 🎯 功能概述

NL2DV 模块将自然语言任务描述和数据表格转换为完整的数据视频，包含：

- **自动场景设计**：根据数据洞察自动生成视频场景（开场、图表、统计卡片、结尾）
- **多种图表类型**：支持柱状图、折线图、饼图、散点图等
- **动画效果**：自动添加入场动画、强调动画等
- **完整视频组装**：自动注册组件并组装成完整视频

## 🏗️ 架构说明

NL2DV 模块包含两个核心子模块：

```
nl2dv/
├── config_generation/     # 配置生成模块
│   ├── 功能: 自然语言 + DataFrame → 视频配置 JSON
│   ├── 输入: 任务描述 + 数据表格
│   └── 输出: 视频配置 JSON（包含 meta、scenes、insights）
│
├── video_generation/      # 视频生成模块
│   ├── 功能: 视频配置 JSON → 完整视频
│   ├── 输入: 视频配置 JSON
│   └── 输出: Remotion 视频组件和完整视频
│
├── pipeline.py            # 统一入口脚本（推荐使用）
└── README.md              # 本文档
```

### 工作流程

```
自然语言描述 + DataFrame
        ↓
[config_generation]
    - Data Analyst: 提取数据洞察
    - Scene Designer: 生成场景配置
    - Animation Coordinator: 添加动画
        ↓
    视频配置 JSON
        ↓
[video_generation]
    - 生成静态 TSX 组件
    - 添加动画效果
    - 注册组件
    - 组装完整视频
        ↓
    完整数据视频
```

## 🚀 快速开始

### 方式1: 使用统一入口脚本（推荐）

使用 `pipeline.py` 一键完成整个流程：

```bash
python -m deepeye.nodes.nl2dv.pipeline \
    --query "生成一个展示科技公司收入的视频" \
    --data data.csv \
    --output-dir ./output
```

### 方式2: 分步执行

#### 步骤1: 生成配置

```python
from deepeye.nodes.nl2dv import NL2DVNode
from deepeye.nodes.io import NodeInput
import pandas as pd

# 准备数据
df = pd.DataFrame({
    'company': ['Apple', 'Microsoft', 'Google'],
    'revenue': [394.3, 211.9, 307.4]
})

# 创建节点
node = NL2DVNode(
    node_id="nl2dv1",
    config={
        "api_key": "sk-...",  # 或设置 DEEPEYE_LLM_API_KEY 环境变量
        "model": "gpt-4o",
        "language": "English"
    }
)

# 生成配置
outputs = node.run({
    "data": NodeInput(data={"dataframe": df}),
    "task": NodeInput(data={"description": "生成一个展示科技公司收入的视频"})
})

config = outputs["config"].data

# 保存配置
import json
with open("config.json", "w", encoding="utf-8") as f:
    json.dump(config, f, ensure_ascii=False, indent=2)
```

#### 步骤2: 生成视频

```bash
python deepeye/nodes/nl2dv/video_generation/pipeline_full_video.py \
    --config config.json \
    --workers 5
```

## 📖 完整工作流程

### 1. 配置生成阶段（config_generation）

**输入**：
- 自然语言任务描述
- DataFrame 数据

**处理**：
1. **Data Analyst**：分析数据，提取关键洞察
2. **Scene Designer**：根据洞察设计视频场景结构
3. **Animation Coordinator**：为场景添加动画效果（可选）

**输出**：
- 视频配置 JSON 文件，包含：
  - `meta`: 视频元数据（标题、分辨率、帧率等）
  - `scenes`: 场景列表（opening、chart、stat_cards、closing）
  - `insights`: 数据洞察

### 2. 视频生成阶段（video_generation）

**输入**：
- 视频配置 JSON 文件

**处理**：
1. **生成静态组件**：为每个场景生成 TSX 组件
2. **添加动画**：为组件添加动画效果
3. **注册组件**：自动注册到 Remotion Root.tsx
4. **组装视频**：创建完整视频 Composition

**输出**：
- Remotion 视频组件
- 完整视频 Composition（可在 Remotion Studio 中预览）

## 📦 模块说明

### config_generation/

负责从自然语言和 DataFrame 生成视频配置 JSON。

**主要组件**：
- `NL2DVNode`: 节点接口，可在工作流中使用
- `SimpleConfigGenerator`: 配置生成器
- `NL2DVConfig`: 节点配置类

**详细文档**: [config_generation/README.md](config_generation/README.md)

### video_generation/

负责从配置 JSON 生成完整的 Remotion 视频。

**主要脚本**：
- `pipeline_full_video.py`: 完整视频生成流水线
- `generate_with_claude.py`: 生成图表场景静态组件
- `generate_other_scenes.py`: 生成其他场景（opening/closing/stat_cards）
- `add_animations_to_static.py`: 为图表场景添加动画
- `add_animations_to_other_scenes.py`: 为其他场景添加动画
- `auto_register_components.py`: 自动注册组件
- `auto_compose_video.py`: 组装完整视频

## 💡 使用示例

### 示例1: 基本使用（命令行）

```bash
# 使用统一入口脚本
python -m deepeye.nodes.nl2dv.pipeline \
    --query "展示2023年各季度销售额趋势" \
    --data sales_data.csv \
    --output-dir ./output \
    --language Chinese \
    --workers 5
```

### 示例2: 使用已有配置

```bash
# 如果已有配置文件，可以跳过配置生成
python -m deepeye.nodes.nl2dv.pipeline \
    --config existing_config.json \
    --skip-config-generation \
    --output-dir ./output
```

### 示例3: Python API

```python
from deepeye.nodes.nl2dv import NL2DVNode
from deepeye.nodes.io import NodeInput
import pandas as pd
import json

# 准备数据
df = pd.read_csv("data.csv")

# 创建节点
node = NL2DVNode(
    node_id="nl2dv1",
    config={
        "api_key": os.getenv("DEEPEYE_LLM_API_KEY"),
        "model": "gpt-4o",
        "language": "English",
        "verbose": True
    }
)

# 生成配置
outputs = node.run({
    "data": NodeInput(data={"dataframe": df}),
    "task": NodeInput(data={"description": "生成销售数据视频"})
})

if outputs["config"].status == "success":
    config = outputs["config"].data
    
    # 保存配置
    with open("config.json", "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)
    
    print(f"✅ 配置生成成功！")
    print(f"   视频标题: {config['meta']['title']}")
    print(f"   场景数量: {len(config['scenes'])}")
else:
    print(f"❌ 配置生成失败")
```

### 示例4: 多 DataFrame 输入

```python
df1 = pd.DataFrame({'month': ['Jan', 'Feb'], 'sales': [100, 150]})
df2 = pd.DataFrame({'category': ['A', 'B'], 'value': [10, 20]})

outputs = node.run({
    "data": NodeInput(data={"dataframe_list": [df1, df2]}),
    "task": NodeInput(data={"description": "创建对比视频"})
})
```

## ⚙️ 配置选项

### LLM 配置

```python
config = {
    # LLM 配置
    "api_key": "sk-...",  # 或从环境变量 DEEPEYE_LLM_API_KEY 读取
    "base_url": "https://api.openai.com/v1",
    "model": "gpt-4o",
    "temperature": 0.7,
    
    # 生成配置
    "language": "English",  # 或 "Chinese"
    "skip_animations": False,  # 是否跳过动画生成
    
    # 视频元数据（可选）
    "fps": 30,
    "width": 1280,
    "height": 720,
    
    # 调试
    "verbose": False
}
```

### 命令行参数

**pipeline.py 参数**：
- `--query`: 自然语言任务描述（必需，除非使用 `--skip-config-generation`）
- `--data`: 数据文件路径（CSV/JSON/Excel）（必需，除非使用 `--skip-config-generation`）
- `--config`: 配置文件路径（如果已有配置）
- `--output-dir`: 输出目录（默认：`./output`）
- `--workers`: 并行线程数（默认：`5`）
- `--language`: 输出语言（`English`/`Chinese`，默认：`English`）
- `--skip-config-generation`: 跳过配置生成，直接使用已有配置
- `--skip-animations`: 配置生成时跳过动画生成
- `--skip-static`: 跳过静态图生成
- `--skip-animation`: 跳过动画生成
- `--skip-other-scenes`: 跳过其他场景生成（opening/closing/stat_cards）

## 📚 相关文档

- [config_generation/README.md](config_generation/README.md) - 配置生成模块详细文档
- [video_generation/pipeline_full_video.py](video_generation/pipeline_full_video.py) - 视频生成流水线脚本

## 🎬 支持的场景类型

- **opening**: 开场场景（标题和副标题）
- **chart**: 图表场景（柱状图、折线图、饼图、散点图）
- **stat_cards**: 统计卡片场景（突出显示关键指标）
- **closing**: 结尾场景（总结）

## 📊 支持的图表类型

- `bar_chart`: 柱状图（用于对比/数量）
- `line_chart`: 折线图（用于趋势/时间序列）
- `pie_chart`: 饼图（用于部分与整体关系）
- `scatter_chart`: 散点图（用于相关性/分布）

## ⚠️ 注意事项

1. **API Key**: 必须提供 LLM API Key（通过配置或环境变量 `DEEPEYE_LLM_API_KEY`）
2. **数据格式**: 输入必须是 pandas DataFrame
3. **生成时间**: 多阶段生成可能需要较长时间（配置生成：3 次 LLM 调用）
4. **配置格式**: 输出配置不包含时间字段，由后续的音频对齐模块处理
5. **Remotion**: 视频生成需要在 Remotion 项目环境中运行

## 🔧 故障排除

### 配置生成失败

- 检查 API Key 是否正确设置
- 检查数据格式是否正确
- 查看详细日志（使用 `--verbose` 参数）

### 视频生成失败

- 确保配置文件格式正确
- 检查 Remotion 环境是否正确设置
- 查看各步骤的错误信息

## 🚀 下一步

生成完成后：

1. 在 Remotion Studio 中查看完整视频
2. 可以预览单个场景或完整串联视频
3. 如果 Remotion Studio 未运行，执行: `npm start`

