# DataPlot 节点 - 智能数据可视化

## 📖 概述

`DataPlotNode` 是一个基于 LLM 的智能数据可视化节点，能够将自然语言描述转换为 Python 可视化代码并在沙盒中安全执行。

**核心特性**：
- 🤖 **自然语言驱动**：用自然语言描述可视化需求，无需编写代码
- 🔄 **自动错误修复**：内置多轮错误修复机制，提高成功率
- 📊 **多种图表类型**：支持折线图、柱状图、散点图、热力图等
- 🔢 **多 DataFrame 支持**：可同时处理多个数据集
- 🎨 **多图输出**：一次生成多个图表
- 🔒 **安全执行**：基于 Docker 沙盒的隔离执行环境
- 💡 **Code Filling 模式**：LLM 只需生成核心可视化代码，DataFrame 和环境已准备好

---

## 🏗️ 架构设计

### Code Filling 模式

与 `DataCoderNode` 类似，`DataPlotNode` 采用 **Code Filling** 任务设计：

```python
# === 模板前部分（自动生成）===
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

# DataFrame 已经准备好
df = <deserialized_dataframe>  # 单 DataFrame 模式
# 或
df0, df1, df2 = <deserialized_dataframes>  # 多 DataFrame 模式

# 图片保存目录已设置
PLOT_DIR = "/sandbox/plots"

# === LLM 生成的代码（填充部分）===
# 用户只需要关注可视化逻辑
fig, ax = plt.subplots()
ax.plot(df['x'], df['y'])
plt.savefig(f'{PLOT_DIR}/chart.png')
plt.close()
print('PLOT_FILE: chart.png|描述|png')
# === 结束 ===
```

**优势**：
1. LLM 明确知道 DataFrame 变量已经存在
2. 不需要处理数据序列化/反序列化
3. 专注于可视化逻辑，提高代码质量
4. 与 DataCoderNode 保持一致的设计模式

---

## 🚀 快速开始

### 安装依赖

```bash
# 基础依赖
pip install pandas matplotlib seaborn

# 沙盒执行依赖
pip install 'llm-sandbox[docker]'

# LLM 客户端
pip install openai  # 或其他 LLM 客户端
```

### 基本使用

```python
import pandas as pd
from deepeye.nodes.dataplot import DataPlotNode
from deepeye.nodes.io import NodeInput

# 准备数据
df = pd.DataFrame({
    'month': ['Jan', 'Feb', 'Mar', 'Apr'],
    'sales': [100, 150, 120, 180]
})

# 创建节点
node = DataPlotNode(
    node_id="plot1",
    config={
        "api_key": "sk-...",
        "model": "gpt-4",
        "verbose": True
    }
)

# 执行可视化
outputs = node.run({
    "data": NodeInput(data={"dataframe": df}),
    "task": NodeInput(data={"description": "绘制月度销售额折线图"})
})

# 获取结果
images = outputs["images"].data
for image in images:
    print(f"文件名: {image['filename']}")
    print(f"描述: {image['description']}")
    
    # 保存图片
    with open(image['filename'], 'wb') as f:
        f.write(image['data'])
```

---

## 📋 输入输出

### 输入端口

#### 1. `data` 端口

**单 DataFrame 模式**：
```python
{
    "dataframe": pd.DataFrame(...)
}
```

**多 DataFrame 模式**：
```python
{
    "dataframe_list": [df0, df1, df2, ...]
}
```

#### 2. `task` 端口

```python
{
    "description": "自然语言描述的可视化任务"
}
```

**任务描述示例**：
- "绘制月度销售额的折线图"
- "创建两个子图：左边是销售趋势，右边是成本对比"
- "生成一个散点图，X轴是年龄，Y轴是收入，按类别着色"
- "创建热力图显示相关性矩阵"

### 输出端口

#### `images` 端口

返回图片列表，每个图片包含：

```python
{
    "data": bytes,              # 图片字节数据
    "filename": str,            # 文件名（如 "sales_chart.png"）
    "description": str,         # 图片描述
    "format": str,              # 图片格式（"png", "jpg", "svg" 等）
    "file_size": int            # 文件大小（字节）
}
```

**元数据**：
```python
{
    "success": bool,            # 是否成功
    "code": str,                # 生成的代码
    "packages": list[str],      # 使用的包
    "retries": int,             # 重试次数
    "image_count": int,         # 图片数量
    "is_multi_mode": bool,      # 是否多 DataFrame 模式
    "execution_log": list,      # 执行日志
    "task_description": str     # 任务描述
}
```

---

## 🎨 使用示例

### 示例 1: 单 DataFrame 简单图表

```python
df = pd.DataFrame({
    'month': ['Jan', 'Feb', 'Mar', 'Apr', 'May'],
    'sales': [100, 150, 120, 180, 200]
})

outputs = node.run({
    "data": NodeInput(data={"dataframe": df}),
    "task": NodeInput(data={"description": "绘制月度销售额折线图"})
})
```

### 示例 2: 一次生成多个图表

```python
df = pd.DataFrame({
    'product': ['A', 'B', 'C', 'D'],
    'sales': [100, 150, 120, 180],
    'profit': [20, 35, 25, 45]
})

outputs = node.run({
    "data": NodeInput(data={"dataframe": df}),
    "task": NodeInput(data={
        "description": """
        创建三个图表：
        1. 产品销售额的柱状图
        2. 产品利润的饼图
        3. 销售额和利润的对比图
        """
    })
})

# 输出: 3 个图片
```

### 示例 3: 多 DataFrame 可视化

```python
df1 = pd.DataFrame({
    'year': [2020, 2021, 2022, 2023],
    'revenue': [100, 120, 150, 180]
})

df2 = pd.DataFrame({
    'department': ['Sales', 'Marketing', 'R&D'],
    'budget': [500, 300, 600]
})

outputs = node.run({
    "data": NodeInput(data={"dataframe_list": [df1, df2]}),
    "task": NodeInput(data={
        "description": """
        创建一个包含两个子图的图表：
        - 左边：df0 的年度收入折线图
        - 右边：df1 的各部门预算柱状图
        """
    })
})
```

### 示例 4: 高级可视化

```python
df = pd.DataFrame({
    'age': [25, 30, 35, 40, 45],
    'income': [50000, 60000, 75000, 90000, 100000],
    'satisfaction': [7, 8, 6, 9, 8],
    'category': ['A', 'B', 'A', 'C', 'B']
})

outputs = node.run({
    "data": NodeInput(data={"dataframe": df}),
    "task": NodeInput(data={
        "description": """
        创建散点图：
        - X轴：年龄
        - Y轴：收入
        - 颜色：按类别分组
        - 大小：按满意度调整点的大小
        - 添加趋势线
        """
    })
})
```

---

## ⚙️ 配置选项

### 完整配置

```python
config = {
    # === LLM 配置 ===
    "api_key": "sk-...",                    # API Key（可选，默认从环境变量读取）
    "base_url": "https://api.openai.com/v1",  # API Base URL
    "model": "gpt-4",                       # 模型名称
    "temperature": 0.1,                     # 温度参数（0-1）
    
    # === 执行配置 ===
    "max_retries": 3,                       # 最大错误修复重试次数
    "timeout": 60,                          # 代码执行超时时间（秒）
    "libraries": ["matplotlib", "seaborn"], # 可用的 Python 库
    
    # === 可视化配置 ===
    "sandbox_plot_dir": "/sandbox/plots",   # 沙盒中的图片保存目录
    
    # === 调试配置 ===
    "verbose": False                        # 是否输出详细日志
}

node = DataPlotNode(node_id="plot1", config=config)
```

### 关键配置说明

#### `model`
推荐使用 `gpt-4` 或 `gpt-4-turbo`，代码生成质量更高。

#### `max_retries`
- 默认：3
- 建议：2-5
- 说明：LLM 生成的代码可能第一次失败，通过多轮修复提高成功率

#### `timeout`
- 默认：60 秒
- 建议：根据数据量和图表复杂度调整
- 大数据集或复杂图表可能需要更长时间

#### `libraries`
- 默认：`["matplotlib", "seaborn", "pandas", "numpy"]`
- 可选：`"plotly"`, `"altair"`, `"bokeh"` 等
- 说明：LLM 可以在 `<package_list>` 中指定额外的包

---

## 🔧 高级用法

### 1. 自定义图片格式和质量

```python
outputs = node.run({
    "data": NodeInput(data={"dataframe": df}),
    "task": NodeInput(data={
        "description": """
        绘制高质量的销售趋势图：
        - 使用 DPI=300
        - 保存为 PNG 格式
        - 图片尺寸 12x8 英寸
        - 使用 tight_layout
        """
    })
})
```

### 2. 处理中文字体

```python
outputs = node.run({
    "data": NodeInput(data={"dataframe": df}),
    "task": NodeInput(data={
        "description": """
        绘制中文标题的图表：
        - 标题：'月度销售额趋势'
        - 使用支持中文的字体（如 SimHei 或 Microsoft YaHei）
        - 如果字体不可用，使用 matplotlib 的默认中文字体
        """
    })
})
```

### 3. 使用 Plotly 创建交互式图表

```python
node = DataPlotNode(
    node_id="plot1",
    config={
        "api_key": "sk-...",
        "libraries": ["matplotlib", "seaborn", "plotly"]
    }
)

outputs = node.run({
    "data": NodeInput(data={"dataframe": df}),
    "task": NodeInput(data={
        "description": """
        使用 Plotly 创建交互式折线图：
        - 显示数据点的悬停信息
        - 添加缩放和平移功能
        - 保存为 HTML 文件
        """
    })
})
```

### 4. 错误处理和日志

```python
node = DataPlotNode(
    node_id="plot1",
    config={
        "api_key": "sk-...",
        "verbose": True,  # 启用详细日志
        "max_retries": 5
    }
)

outputs = node.run({
    "data": NodeInput(data={"dataframe": df}),
    "task": NodeInput(data={"description": "..."})
})

result = outputs["images"]

if result.metadata["success"]:
    print(f"成功！重试了 {result.metadata['retries']} 次")
    print(f"生成的代码:\n{result.metadata['code']}")
else:
    print(f"失败: {result.metadata['error']}")
    print("执行日志:")
    for log in result.metadata["execution_log"]:
        print(f"  第 {log['retry']} 轮: {log['error']}")
```

---

## 🎯 支持的图表类型

### 基础图表
- ✅ 折线图（Line Chart）
- ✅ 柱状图（Bar Chart）
- ✅ 饼图（Pie Chart）
- ✅ 散点图（Scatter Plot）
- ✅ 箱线图（Box Plot）
- ✅ 直方图（Histogram）

### 高级图表
- ✅ 热力图（Heatmap）
- ✅ 堆叠柱状图（Stacked Bar）
- ✅ 多系列折线图（Multi-line）
- ✅ 子图布局（Subplots）
- ✅ 双轴图表（Dual Axis）
- ✅ 小提琴图（Violin Plot）

### 交互式图表
- ✅ Plotly 交互式图表
- ✅ Seaborn 统计图表
- ⏳ Altair 声明式图表（即将支持）

---

## 🔍 工作流程

### 内部执行流程

```
1. 接收输入
   ├─ DataFrame(s)
   └─ 任务描述

2. 生成数据信息
   ├─ 形状、列信息
   └─ 示例数据

3. LLM 生成代码（第 1 轮）
   ├─ 发送 Code Filling Prompt
   ├─ LLM 返回 <think> + <package_list> + <code>
   └─ 提取代码和包列表

4. 执行代码
   ├─ 将用户代码插入模板
   ├─ 在沙盒中执行
   └─ 提取图片文件

5. 检查结果
   ├─ 成功 → 返回图片
   └─ 失败 → 进入错误修复

6. 错误修复（最多 max_retries 次）
   ├─ 发送错误修复 Prompt
   ├─ LLM 分析错误并生成修复代码
   └─ 重新执行

7. 返回结果
   ├─ 图片列表（成功）
   └─ 错误信息（失败）
```

### Code Filling 模板

**单 DataFrame 模式**：
```python
# === 前置代码（自动生成）===
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns

df = <deserialized>  # DataFrame 已准备好
PLOT_DIR = "/sandbox/plots"

# === 用户代码（LLM 生成）===
# ... 可视化代码 ...

# === 后置验证（自动处理）===
# 系统自动收集图片文件
```

**多 DataFrame 模式**：
```python
# === 前置代码（自动生成）===
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns

df0 = <deserialized>  # 第一个 DataFrame
df1 = <deserialized>  # 第二个 DataFrame
# ...
PLOT_DIR = "/sandbox/plots"

# === 用户代码（LLM 生成）===
# ... 可视化代码 ...

# === 后置验证（自动处理）===
# 系统自动收集图片文件
```

---

## 🐛 常见问题

### 1. 中文字体乱码

**问题**：生成的图表中文显示为方块  
**解决**：在任务描述中明确要求使用支持中文的字体

```python
"description": "绘制图表，使用 SimHei 字体显示中文标题"
```

### 2. 图片未生成

**问题**：代码执行成功但没有图片  
**原因**：代码中没有调用 `plt.savefig()` 或没有打印 `PLOT_FILE` 信息  
**解决**：在任务描述中明确要求保存图片

```python
"description": "绘制图表并保存为 PNG 文件"
```

### 3. 执行超时

**问题**：大数据集或复杂图表导致超时  
**解决**：增加 `timeout` 配置

```python
config = {"timeout": 120}  # 增加到 120 秒
```

### 4. 包未安装

**问题**：代码需要的包在沙盒中不可用  
**解决**：在 `libraries` 配置中添加所需的包

```python
config = {"libraries": ["matplotlib", "seaborn", "plotly", "scipy"]}
```

---

## 🔒 安全性

### Docker 沙盒隔离

- ✅ 代码在独立的 Docker 容器中执行
- ✅ 无法访问宿主机文件系统
- ✅ 无网络访问（默认）
- ✅ CPU 和内存限制

### 资源限制

- ✅ 执行超时控制
- ✅ 文件大小限制
- ✅ 进程数量限制

### 代码审查

虽然代码在沙盒中执行，但仍建议：
- 审查生成的代码（设置 `verbose=True`）
- 限制可用的库
- 设置合理的超时时间

---

## 📊 性能优化

### 1. 复用容器

全局容器复用机制：
```python
from deepeye.runtime.code_executor import GlobalSandboxContainer

# 容器会自动创建和复用
# 无需手动管理
```

### 2. 减少重试次数

如果 LLM 质量较高，可以减少重试次数：
```python
config = {"max_retries": 1}  # 只重试 1 次
```

### 3. 使用更快的模型

对于简单图表，可以使用更快的模型：
```python
config = {"model": "gpt-3.5-turbo"}
```

---

## 🔗 相关节点

- **DataCoderNode**: 数据处理节点（同样使用 Code Filling 模式）
- **DataSourceNode**: 数据源节点
- **MemoryDataSourceNode**: 内存数据源节点

---

## 📝 完整示例

查看 `examples/dataplot_example.py` 获取更多示例：

```bash
cd /path/to/DeepEye/packages/deepeye-core
export OPENAI_API_KEY="sk-..."
python examples/dataplot_example.py
```

---

## 🚧 未来计划

### 短期（1-2 周）
- [ ] 支持更多可视化库（Altair、Bokeh）
- [ ] 添加图片质量配置（DPI、尺寸）
- [ ] 支持图片格式选择（PNG、JPG、SVG）

### 中期（1-2 月）
- [ ] 图片缓存机制
- [ ] 流式输出支持
- [ ] 图片预览功能

### 长期（3-6 月）
- [ ] 视频生成（动画图表）
- [ ] 交互式仪表板
- [ ] Web UI 集成

---

## 📄 许可证

MIT License

---

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

---

**版本**: v0.1.0  
**作者**: DeepEye Team  
**最后更新**: 2025-10-26

