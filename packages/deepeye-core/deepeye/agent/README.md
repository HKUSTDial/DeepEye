# DeepEye Agent Module

> 智能工作流编排系统 - 将自然语言任务转换为可执行的工作流

## 快速开始

```python
from deepeye.llm import LLMClient
from deepeye.agent import PlannerAgent
from deepeye.nodes import NL2SQLNode, DataPlotNode

# 初始化
llm_client = LLMClient(api_key="your-key")
agent = PlannerAgent(llm_client)

# 注册节点
agent.register_node(NL2SQLNode)
agent.register_node(DataPlotNode)

# 执行任务
result = agent.run("查询销售数据并生成趋势图")

if result.success:
    print("✓ Success!")
    print(result.workflow.to_json())
```

## 模块结构

```
agent/
├── __init__.py           # 导出公共 API
├── tool_layer.py         # ToolRegistry, ToolDescription
├── planner.py            # PlannerAgent
├── models.py             # AgentResult, ExecutionPlan
├── prompts.py            # Prompt 模板
└── strategies/           # 未来的其他策略
    └── __init__.py
```

## 核心组件

### PlannerAgent

基于 Planner-Executor 模式的智能工作流编排器。

**特性**：
- 自动任务分析和规划
- 智能工具选择
- 依赖关系管理
- 自动并行执行

### ToolRegistry

工具注册和管理。

**功能**：
- 节点注册为工具
- 工具发现和查询
- 节点实例创建

### ExecutionPlan

描述完整的任务执行步骤。

**包含**：
- 步骤列表
- 依赖关系
- 参数配置
- 推理过程

## 文档

完整文档请参考：

- 📖 [快速开始指南](../../AGENT_QUICK_START.md)
- 📖 [设计概要](../../AGENT_DESIGN_SUMMARY.md)
- 📖 [完整设计文档](../../AGENT_ORCHESTRATION_DESIGN.md)
- 📖 [文档索引](../../docs/agent_system.md)

## 实现状态

- ✅ 设计完成
- ⏳ 开始实现

## 下一步

1. 实现 `tool_layer.py` - ToolRegistry 和 ToolDescription
2. 实现 `models.py` - 数据模型
3. 实现 `planner.py` - PlannerAgent 核心逻辑
4. 编写测试

详细实现计划请参考 [完整设计文档](../../AGENT_ORCHESTRATION_DESIGN.md#3-实现计划)。

---

**状态**：Design Complete, Implementation Pending  
**最后更新**：2025-11-03

