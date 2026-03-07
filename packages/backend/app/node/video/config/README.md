# Video Generator Node 使用说明

## 概述

`video.generator` 节点用于从数据集引用和用户查询生成完整的数据视频。该节点会自动：
1. 生成视频配置（场景、图表、动画等）
2. **自动生成音频**（使用 Azure Speech TTS）
3. **自动对齐时间戳**（将动画和场景时间与音频同步）
4. **自动渲染视频组件**（生成 Remotion TSX 组件）

## 前置条件

### 1. 安装依赖

需要在 `packages/backend/pyproject.toml` 中添加 Azure Speech SDK 依赖：

```toml
dependencies = [
    # ... 其他依赖 ...
    "azure-cognitiveservices-speech>=1.40.0",
]
```

然后运行：
```bash
uv sync --all-packages --group dev
```

### 2. 配置环境变量

在 `.env` 文件中添加 Azure Speech API 配置：

```env
# Azure Speech TTS Configuration (Required for audio generation)
AZURE_SPEECH_KEY=your-azure-speech-key-here
AZURE_SPEECH_REGION=eastasia
```

**如何获取 Azure Speech API 密钥：**
1. 访问 [Azure Portal](https://portal.azure.com/)
2. 创建或选择 "Speech Services" 资源
3. 在 "Keys and Endpoint" 页面获取 Key 和 Region

### 3. 可选：安装 ffmpeg（用于音频时长检测）

如果系统没有安装 `ffprobe`，音频时长将使用估算值（基于文件大小）。

```bash
# macOS
brew install ffmpeg

# Ubuntu/Debian
sudo apt-get install ffmpeg

# 其他系统请参考 ffmpeg 官方文档
```

## 节点规格

### Node Type
```
video.generator
```

### 输入 (Inputs)
- **dataset_ref** (`dict`): 输入数据集引用，节点会读取其预览/采样数据用于生成视频
- **query** (`string`, 必需): 用户查询或分析目标

### 输出 (Outputs)
- **video_path** (`string`): 生成的视频组件目录路径
- **video_info** (`dict`): 视频生成信息，包含：
  - `status`: 渲染状态（"success", "skipped", "failed"）
  - `task_id`: 任务ID
  - `output_dir`: 输出目录
- **config** (`dict`): 生成的视频配置 JSON，包含：
  - 场景配置（scenes）
  - 时间对齐信息（time_start, time_end）
  - 音频文件路径（audio_file）
  - 动画时间戳
- **config_path** (`string`): 保存的配置文件路径

### 参数 (Params)
- **language** (`string`, 可选): 输出语言，默认为 "English"
  - 支持: "English", "Chinese", "中文" 等
  - 自动转换为语言代码: "en-US", "zh-CN"
- **workers** (`integer`, 可选): 视频渲染并行线程数，默认为 5

## 使用方式

### 方式 1: 在工作流中使用（推荐）

节点会自动注册到工作流系统。你可以在 Workflow Agent 的提示中描述需要使用视频配置生成功能，Agent 会自动生成包含该节点的工作流。

**工作流 JSON 示例：**
```json
{
  "root": {
    "nodes": {
      "video_generator_1": {
        "type": "video.generator",
        "inputs": {
          "dataset_ref": {
            "node_id": "data_source_1",
            "port_id": "dataset_ref"
          },
          "query": {
            "node_id": "user_query_node",
            "port_id": "query"
          }
        },
        "params": {
          "language": "English"
        }
      }
    },
    "edges": [
      {
        "source": {"node_id": "data_source_1", "port_id": "dataset_ref"},
        "target": {"node_id": "video_generator_1", "port_id": "dataset_ref"}
      },
      {
        "source": {"node_id": "user_query_node", "port_id": "query"},
        "target": {"node_id": "video_generator_1", "port_id": "query"}
      }
    ]
    "outputs": {
      "video_path": {
        "node_id": "video_generator_1",
        "port_id": "video_path"
      },
      "config": {
        "node_id": "video_generator_1",
        "port_id": "config"
      }
    }
  }
}
```

### 方式 2: 直接调用（用于测试）

```python
from app.node.video.node import VideoGeneratorHandler

# 创建 handler
handler = VideoGeneratorHandler(db=db, user_id=user_id)

# 准备输入（query 现在是输入端口，表格数据统一通过 dataset_ref 传递）
inputs = {
    "dataset_ref": {
        "kind": "dataset_ref",
        "path": "/workspace/.datasets/revenue.jsonl",
        "format": "jsonl",
        "preview_rows": [
            {"company": "A", "revenue": 100},
            {"company": "B", "revenue": 150}
        ],
        "row_count": 2,
        "columns": ["company", "revenue"]
    },
    "query": "展示各公司的营收对比"
}

# 创建节点
node = Node(
    id="test_node",
    type="video.generator",
    params={
        "language": "English",
        "workers": 5,
    }
)

# 执行
result = handler.execute(node, inputs, context=None)
config = result["config"]
```

## 输出配置格式

生成的配置包含完整的视频配置信息：

```json
{
  "meta": {
    "fps": 30,
    "width": 1280,
    "height": 720,
    "video_duration": 45.2
  },
  "scenes": [
    {
      "id": "scene1",
      "type": "chart",
      "time_range": [0.0, 15.5],
      "narration": [
        {
          "text": "Company A leads with 100 million in revenue",
          "time_start": 0.0,
          "time_end": 3.5,
          "audio_file": "/tmp/video_config_audio/scene1_narr0.wav"
        }
      ],
      "animations": [
        {
          "type": "emphasis",
          "time_start": 0.2,
          "duration": 3.3,
          "trigger_narration": 0
        }
      ]
    }
  ]
}
```

## 音频生成说明

### 自动生成
- 音频生成是**默认行为**，无需额外配置
- 如果 Azure Speech API 未配置，节点会返回基础配置（不含时间字段）

### 音频文件存储
- 音频文件存储在 `/tmp/video_config_audio/` 目录
- 配置中的 `audio_file` 字段包含音频文件的路径

### 时间对齐
- 自动计算每个旁白的 `time_start` 和 `time_end`
- 自动对齐动画时间戳（基于 `trigger_narration` 字段）
- 自动计算场景的 `time_range`
- 自动计算视频总时长

## 错误处理

节点具有容错机制：

1. **Azure Speech API 未配置**
   - 返回基础配置（不含时间字段）
   - 记录警告日志

2. **音频生成失败**
   - 返回基础配置（不含时间字段）
   - 记录错误日志

3. **无旁白数据**
   - 返回基础配置
   - 记录警告日志

## 故障排查

### 问题：音频生成失败

1. **检查环境变量**
   ```bash
   # 确认 .env 文件中有正确的配置
   cat .env | grep AZURE_SPEECH
   ```

2. **检查依赖安装**
   ```bash
   python -c "import azure.cognitiveservices.speech; print('OK')"
   ```

3. **检查日志**
   - 查看后端日志中的警告或错误信息
   - 日志会显示具体的失败原因

### 问题：时间对齐不正确

- 确保配置中有 `narration` 字段
- 确保 `trigger_narration` 索引正确
- 检查音频文件是否成功生成

## 技术细节

### 语言代码映射
- "English" / "英文" → "en-US"
- "Chinese" / "中文" → "zh-CN"
- 默认: "en-US"

### 音频生成流程
1. 提取所有场景的旁白文本
2. 批量生成音频文件（并行处理，最多 2 个并发）
3. 捕获词级别时间戳（word-level timestamps）
4. 使用时间对齐器计算时间字段

### 时间对齐算法
- 基于音频文件的实际时长
- 使用词级别时间戳进行精确对齐
- 支持动画与旁白的同步（narration-animation interplay）
