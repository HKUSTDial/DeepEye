# NL2DV 节点

自然语言转数据视频配置节点（Natural Language to Data Video）。

## 功能概述

该节点接收自然语言描述和 DataFrame，通过 LLM 生成视频配置 JSON。包含多智能体生成流程：

1. **Data Analyst**: 提取数据洞察
2. **Scene Designer**: 生成完整视频场景配置
3. **Animation Coordinator**: 添加动画效果（可选）

## 输入输出

### 输入端口

- **data**: DataFrame 或 DataFrame 列表
  - 支持单个 DataFrame: `{"dataframe": df}`
  - 支持多个 DataFrame: `{"dataframe_list": [df1, df2, ...]}`
  
- **task**: 任务描述（自然语言）
  - `{"description": "生成一个展示销售趋势的视频"}`

### 输出端口

- **config**: 视频配置 JSON
  - 包含 `meta`（元数据）、`scenes`（场景列表）、`insights`（洞察）等

## 配置选项

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

## 使用示例

### 基本使用

```python
from deepeye.nodes.nl2dv import NL2DVNode
from deepeye.nodes.io import NodeInput
import pandas as pd

# 创建节点
node = NL2DVNode(
    node_id="nl2dv1",
    config={
        "api_key": "sk-...",
        "model": "gpt-4o",
        "language": "English"
    }
)

# 准备数据
df = pd.DataFrame({
    'company': ['Apple', 'Microsoft', 'Google'],
    'revenue': [394.3, 211.9, 307.4]
})

# 执行节点
outputs = node.run({
    "data": NodeInput(data={"dataframe": df}),
    "task": NodeInput(data={"description": "生成一个展示科技公司收入的视频"})
})

# 获取配置
config = outputs["config"].data
print(f"视频标题: {config['meta']['title']}")
print(f"场景数量: {len(config['scenes'])}")
```

### 多 DataFrame 输入

```python
df1 = pd.DataFrame({'month': ['Jan', 'Feb'], 'sales': [100, 150]})
df2 = pd.DataFrame({'category': ['A', 'B'], 'value': [10, 20]})

outputs = node.run({
    "data": NodeInput(data={"dataframe_list": [df1, df2]}),
    "task": NodeInput(data={"description": "创建对比视频"})
})
```

### 中文输出

```python
node = NL2DVNode(
    config={
        "api_key": "sk-...",
        "language": "Chinese"  # 使用中文
    }
)
```

### 跳过动画生成

```python
node = NL2DVNode(
    config={
        "api_key": "sk-...",
        "skip_animations": True  # 跳过动画生成，加快速度
    }
)
```

## 输出配置格式

生成的配置 JSON 格式如下：

```json
{
  "meta": {
    "title": "视频标题",
    "fps": 30,
    "width": 1280,
    "height": 720
  },
  "scenes": [
    {
      "id": "scene_opening",
      "type": "opening",
      "content": {
        "title": "主标题",
        "subtitle": "副标题"
      },
      "narration": [
        {"text": "开场旁白"}
      ]
    },
    {
      "id": "scene_chart_1",
      "type": "chart",
      "content": {
        "chart_type": "bar_chart",
        "title": "图表标题",
        "data": [...],
        "data_binding": {
          "x_axis": {"field": "company", "label": "Company"},
          "y_axis": {"field": "revenue", "label": "Revenue"}
        },
        "style": {...},
        "layout": {...}
      },
      "narration": [
        {"text": "图表介绍"},
        {"text": "具体数据点说明"}
      ],
      "animations": [
        {
          "id": "entrance_anim",
          "type": "entrance",
          "effect": "grow_bars",
          "trigger_narration": 0
        },
        {
          "id": "emphasis_1",
          "type": "emphasis",
          "effect": "pulse",
          "trigger_narration": 1,
          "target_data": {
            "data_filter": {"company": "Apple"}
          }
        }
      ]
    }
  ]
}
```

## 支持的图表类型

- `bar_chart`: 柱状图
- `line_chart`: 折线图
- `pie_chart`: 饼图
- `scatter_chart`: 散点图

## 支持的场景类型

- `opening`: 开场场景
- `chart`: 图表场景
- `stat_cards`: 统计卡片场景
- `closing`: 结束场景

## 工作流集成

```python
from deepeye.workflow import WorkflowBuilder

builder = WorkflowBuilder()

# 数据源节点
db_node = builder.add_node("DatabaseDataSource", ...)

# NL2SQL 节点
sql_node = builder.add_node("NL2SQL", ...)
builder.connect(db_node, sql_node)

# NL2DV 节点
dv_node = builder.add_node("NL2DV", config={...})
builder.connect(sql_node, dv_node)

# 执行工作流
workflow = builder.build()
results = workflow.execute()
```

## 注意事项

1. **API Key**: 必须提供 LLM API Key（通过配置或环境变量）
2. **数据格式**: 输入必须是 pandas DataFrame
3. **生成时间**: 多阶段生成可能需要较长时间（3 次 LLM 调用）
4. **多 DataFrame**: 当前版本使用第一个 DataFrame，未来版本将支持合并策略
5. **配置格式**: 输出配置不包含时间字段，由后续的音频对齐模块处理

## 错误处理

节点包含完善的错误处理机制：

- 输入验证失败：返回错误信息
- LLM 调用失败：使用兜底配置
- JSON 解析失败：返回错误信息

## 性能优化

- 使用 `skip_animations=True` 可以跳过动画生成，减少一次 LLM 调用
- 使用 `verbose=False` 可以减少日志输出
- 大数据集会自动采样（前 50 条记录）用于 prompt，但图表数据会使用完整数据集

