# DeepEye Examples

本目录包含 DeepEye 框架的使用示例。

## Planner Agent 使用示例

`planner_agent_usage.py` 展示了如何使用 PlannerAgent 从自然语言任务生成并执行工作流。

### 配置

在运行示例之前，需要配置以下环境变量：

```bash
# 必需：LLM API 密钥
export DEEPEYE_LLM_API_KEY="sk-..."

# 可选：LLM API 基础 URL（默认为 OpenAI）
export DEEPEYE_LLM_BASE_URL="https://api.openai.com/v1"

# 可选：LLM 模型名称（默认为 gpt-3.5-turbo）
export DEEPEYE_LLM_MODEL="gpt-4"
```

### 常见 LLM 提供商配置

#### OpenAI
```bash
export DEEPEYE_LLM_API_KEY="sk-..."
export DEEPEYE_LLM_BASE_URL="https://api.openai.com/v1"
export DEEPEYE_LLM_MODEL="gpt-4"
```

#### 通义千问（阿里云）
```bash
export DEEPEYE_LLM_API_KEY="sk-..."
export DEEPEYE_LLM_BASE_URL="https://dashscope.aliyuncs.com/compatible-mode/v1"
export DEEPEYE_LLM_MODEL="qwen-turbo"
```

#### DeepSeek
```bash
export DEEPEYE_LLM_API_KEY="sk-..."
export DEEPEYE_LLM_BASE_URL="https://api.deepseek.com/v1"
export DEEPEYE_LLM_MODEL="deepseek-chat"
```

#### Moonshot（月之暗面）
```bash
export DEEPEYE_LLM_API_KEY="sk-..."
export DEEPEYE_LLM_BASE_URL="https://api.moonshot.cn/v1"
export DEEPEYE_LLM_MODEL="moonshot-v1-8k"
```

#### 本地 Ollama
```bash
export DEEPEYE_LLM_API_KEY="ollama"  # Ollama 不需要真实密钥
export DEEPEYE_LLM_BASE_URL="http://localhost:11434/v1"
export DEEPEYE_LLM_MODEL="llama2"
```

### 运行示例

```bash
cd /home/liboyan/project/DeepEye/packages/deepeye-core
uv run python examples/planner_agent_usage.py
```

### 示例说明

脚本包含 4 个示例，展示不同的使用场景：

1. **示例1：简单任务**
   - 从 CSV 文件加载数据
   - 筛选和排序数据
   - 展示基本的工作流生成

2. **示例2：数据库查询**
   - 连接数据库
   - 使用 NL2SQL 自然语言查询
   - 生成可视化图表
   - 展示多节点协作

3. **示例3：复杂流水线**
   - 从 Excel 加载数据
   - 多步骤数据处理
   - 使用 DataCoder 进行智能转换
   - 生成可视化
   - 展示复杂工作流

4. **示例4：完整执行**
   - 生成并自动执行工作流
   - 展示端到端的执行流程
   - 查看执行结果

### 可用节点

示例中注册了所有可用的节点类型：

- **数据库节点**
  - `DatabaseDataSourceNode`: 数据库数据源
  - `NL2SQLNode`: 自然语言转 SQL

- **智能处理节点**
  - `DataCoderNode`: 智能 DataFrame 处理
  - `DataPlotNode`: 智能数据可视化

- **数据源节点**
  - `MemoryDataSourceNode`: 内存数据源
  - `FileDataSourceNode`: 通用文件数据源
  - `CSVDataSourceNode`: CSV 文件数据源
  - `JSONDataSourceNode`: JSON 文件数据源
  - `ExcelDataSourceNode`: Excel 文件数据源

- **处理节点**
  - `FilterNode`: 通用过滤节点
  - `RowFilterNode`: 行过滤节点
  - `ColumnSelectNode`: 列选择节点
  - `TransformNode`: 数据转换节点

### 输出说明

运行示例后，您将看到：

1. **配置信息**：显示使用的 LLM 配置
2. **注册节点**：列出所有已注册的节点工具
3. **执行日志**：显示 Agent 的执行过程
4. **执行计划**：LLM 生成的结构化计划
5. **工作流信息**：生成的工作流结构
6. **执行结果**：如果自动执行，显示最终结果

### 自定义使用

您可以修改脚本中的任务描述来测试不同的场景：

```python
from deepeye.llm import LLMClient
from deepeye.agent import PlannerAgent
from deepeye.nodes.database import DatabaseDataSourceNode

# 创建 LLM 客户端
llm_client = LLMClient(
    api_key=os.getenv("DEEPEYE_LLM_API_KEY"),
    base_url=os.getenv("DEEPEYE_LLM_BASE_URL", "https://api.openai.com/v1"),
)

# 创建 Agent
agent = PlannerAgent(llm_client, model=os.getenv("DEEPEYE_LLM_MODEL", "gpt-4"))

# 注册节点
agent.register_node(DatabaseDataSourceNode)
# ... 注册其他节点 ...

# 运行任务
result = agent.run("你的自然语言任务描述", auto_execute=False)

# 检查结果
if result.success:
    print("✓ 成功!")
    print(f"工作流: {result.workflow.to_json()}")
else:
    print(f"✗ 失败: {result.error}")
```

### 故障排查

如果遇到问题：

1. **环境变量未设置**
   ```
   ❌ 配置错误: 未设置环境变量 DEEPEYE_LLM_API_KEY
   ```
   解决：设置 `DEEPEYE_LLM_API_KEY` 环境变量

2. **LLM API 错误**
   ```
   ❌ LLM认证失败: ...
   ```
   解决：检查 API Key 和 Base URL 是否正确

3. **工作流验证失败**
   ```
   ❌ 工作流验证失败: ...
   ```
   解决：查看详细错误信息，可能是 LLM 生成的计划有问题，可以尝试：
   - 使用更强大的模型（如 gpt-4）
   - 调整任务描述使其更清晰
   - 增加重试次数

### 进一步学习

- 查看 [Agent 文档](../deepeye/agent/README.md)（如果存在）
- 查看 [节点开发指南](../deepeye/nodes/README.md)（如果存在）
- 查看单元测试了解更多用法：`tests/agent/`

