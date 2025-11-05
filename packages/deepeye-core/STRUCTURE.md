# DeepEye Core 目录结构说明

## 目录树

```
deepeye-core/
├── README.md                        # 项目说明
├── pyproject.toml                   # Poetry 配置文件
├── .gitignore                       # Git 忽略配置
├── STRUCTURE.md                     # 本文档
│
├── deepeye/                         # 主包目录
│   ├── __init__.py                  # 包初始化，导出主要 API
│   ├── __version__.py               # 版本信息
│   ├── exceptions.py                # 异常定义
│   │
│   ├── nodes/                       # 🧩 节点系统
│   │   ├── __init__.py              # 导出 BaseNode 和节点注册表
│   │   ├── base.py                  # [待创建] 基础节点类
│   │   ├── registry.py              # [待创建] 节点注册表
│   │   ├── io/                      # 节点输入输出定义
│   │   ├── datasource/              # 数据源节点
│   │   ├── nl2sql/                  # NL2SQL 节点
│   │   ├── nl2code/                 # NL2Code 节点
│   │   ├── visualization/           # 可视化节点
│   │   ├── processing/              # 数据处理节点
│   │   ├── report/                  # 报告生成节点
│   │   ├── rag/                     # RAG 检索节点
│   │   └── video/                   # 视频生成节点
│   │
│   ├── workflow/                    # 🔄 工作流引擎
│   │   ├── __init__.py              # 导出 Workflow 和 WorkflowBuilder
│   │   ├── engine.py                # [待创建] 工作流引擎
│   │   ├── builder.py               # [待创建] 工作流构建器
│   │   ├── graph.py                 # [待创建] 工作流图结构
│   │   ├── validator.py             # [待创建] 工作流验证器
│   │   └── serializer.py            # [待创建] 序列化/反序列化
│   │
│   ├── runtime/                     # ⚡ 执行运行时
│   │   ├── __init__.py              # 导出 WorkflowExecutor
│   │   ├── executor.py              # [待创建] 执行器
│   │   ├── scheduler.py             # [待创建] 调度器
│   │   ├── context.py               # [待创建] 执行上下文
│   │   └── hooks.py                 # [待创建] 执行钩子
│   │
│   ├── agent/                       # 🤖 智能编排器
│   │   ├── __init__.py              # 导出 AgentOrchestrator
│   │   ├── orchestrator.py          # [待创建] 编排器主类
│   │   ├── strategies/              # 编排策略
│   │   │   ├── react.py             # [待创建] ReAct 策略
│   │   │   ├── planner_executor.py  # [待创建] Planner-Executor
│   │   │   ├── rewoo.py             # [待创建] ReWOO 策略
│   │   │   └── todo_driven.py       # [待创建] TODO-Driven
│   │   ├── planner.py               # [待创建] 任务规划器
│   │   └── selector.py              # [待创建] 策略选择器
│   │
│   ├── optimizer/                   # 🚀 优化引擎
│   │   ├── __init__.py              # 导出优化相关类
│   │   ├── engine.py                # [待创建] 优化引擎主类
│   │   ├── parallel.py              # [待创建] 并行执行优化
│   │   ├── cache.py                 # [待创建] 缓存优化
│   │   ├── rag_enhancer.py          # [待创建] RAG 增强
│   │   └── model_router.py          # [待创建] 模型路由
│   │
│   ├── plugin/                      # 🔌 插件系统
│   │   ├── __init__.py              # 导出插件管理器
│   │   ├── manager.py               # [待创建] 插件管理器
│   │   ├── loader.py                # [待创建] 插件加载器
│   │   └── base.py                  # [待创建] 插件基类
│   │
│   ├── llm/                         # 🧠 LLM 集成
│   │   ├── __init__.py              # 导出 LLM 提供商
│   │   ├── providers/               # LLM 提供商
│   │   │   ├── openai.py            # [待创建] OpenAI
│   │   │   ├── anthropic.py         # [待创建] Anthropic
│   │   │   ├── local.py             # [待创建] 本地模型
│   │   │   └── azure.py             # [待创建] Azure OpenAI
│   │   ├── prompts/                 # Prompt 模板
│   │   └── utils.py                 # [待创建] LLM 工具函数
│   │
│   ├── storage/                     # 💾 存储抽象
│   │   ├── __init__.py              # 导出存储后端
│   │   ├── backends/                # 存储后端
│   │   │   ├── local.py             # [待创建] 本地文件系统
│   │   │   ├── s3.py                # [待创建] S3 存储
│   │   │   └── database.py          # [待创建] 数据库存储
│   │   └── serializers/             # 序列化器
│   │
│   ├── observability/               # 👁️ 可观测性
│   │   ├── __init__.py              # 导出日志、指标等
│   │   ├── logger.py                # [待创建] 日志系统
│   │   ├── metrics.py               # [待创建] 指标收集
│   │   ├── tracing.py               # [待创建] 链路追踪
│   │   └── events.py                # [待创建] 事件系统
│   │
│   └── utils/                       # 🛠️ 工具函数
│       ├── __init__.py              # 导出工具函数
│       ├── validators.py            # [待创建] 验证工具
│       ├── serializers.py           # [待创建] 序列化工具
│       └── helpers.py               # [待创建] 辅助函数
│
├── tests/                           # 🧪 测试
│   ├── __init__.py
│   ├── conftest.py                  # Pytest 配置和 fixtures
│   ├── nodes/                       # 节点测试
│   ├── workflow/                    # 工作流测试
│   ├── agent/                       # 编排器测试
│   └── integration/                 # 集成测试
│
└── examples/                        # 💡 使用示例
    ├── basic_workflow.py            # [待创建] 基础工作流示例
    ├── custom_node.py               # [待创建] 自定义节点示例
    └── agent_orchestration.py       # [待创建] Agent 编排示例
```

## 开发顺序建议

### Phase 1: 核心基础 (优先级: ⭐⭐⭐⭐⭐)

1. **节点系统基础**
   - `nodes/io/` - 定义节点的输入输出接口
   - `nodes/base.py` - 基础节点抽象类
   - `nodes/registry.py` - 节点注册表

2. **工作流引擎**
   - `workflow/graph.py` - 工作流图结构（基于 networkx）
   - `workflow/builder.py` - 工作流构建器
   - `workflow/validator.py` - 工作流验证（检查循环依赖等）
   - `workflow/engine.py` - 工作流引擎主类

3. **执行运行时**
   - `runtime/context.py` - 执行上下文
   - `runtime/executor.py` - 执行器

### Phase 2: 基础节点实现 (优先级: ⭐⭐⭐⭐)

4. **简单节点实现**
   - `nodes/datasource/` - 数据源节点（本地文件、SQLite）
   - `nodes/processing/` - 数据处理节点（简单转换）
   - `nodes/visualization/` - 可视化节点（Plotly）

### Phase 3: AI 能力集成 (优先级: ⭐⭐⭐⭐)

5. **LLM 集成**
   - `llm/providers/openai.py` - OpenAI 集成
   - `llm/prompts/` - Prompt 模板

6. **智能节点**
   - `nodes/nl2sql/` - NL2SQL 节点
   - `nodes/nl2code/` - NL2Code 节点

### Phase 4: 智能编排 (优先级: ⭐⭐⭐)

7. **Agent 编排器**
   - `agent/orchestrator.py` - 编排器主类
   - `agent/strategies/react.py` - ReAct 策略
   - `agent/planner.py` - 任务规划器

### Phase 5: 优化和增强 (优先级: ⭐⭐)

8. **优化引擎**
   - `optimizer/parallel.py` - 并行执行优化
   - `optimizer/cache.py` - 缓存优化

9. **可观测性**
   - `observability/logger.py` - 日志系统
   - `observability/metrics.py` - 指标收集

### Phase 6: 扩展性 (优先级: ⭐)

10. **插件系统**
    - `plugin/manager.py` - 插件管理器
    - `plugin/loader.py` - 插件加载器

## 当前状态

✅ 已完成：
- [x] 目录结构创建
- [x] 配置文件（pyproject.toml）
- [x] 异常定义（exceptions.py）
- [x] 测试配置（conftest.py）
- [x] 版本信息（__version__.py）
- [x] 主包初始化（__init__.py）

⏳ 待开发：
- [ ] 节点系统基础
- [ ] 工作流引擎
- [ ] 执行运行时
- [ ] 其他所有模块...

## 开发指南

### 代码风格

- 遵循 PEP 8 规范
- 使用 Black 进行代码格式化（line-length=100）
- 使用 isort 进行导入排序
- 使用 mypy 进行类型检查

### 类型提示

所有公共函数和方法都应该有类型提示：

```python
from typing import List, Dict, Any, Optional

def process_data(
    data: List[Dict[str, Any]], 
    config: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    """处理数据
    
    Args:
        data: 输入数据列表
        config: 可选的配置字典
        
    Returns:
        处理后的数据列表
    """
    ...
```

### 文档字符串

使用 Google 风格的文档字符串：

```python
def function_name(arg1: str, arg2: int) -> bool:
    """简短描述
    
    详细描述（可选）
    
    Args:
        arg1: 第一个参数的描述
        arg2: 第二个参数的描述
        
    Returns:
        返回值的描述
        
    Raises:
        ValueError: 何时抛出此异常
        
    Example:
        >>> function_name("test", 42)
        True
    """
    ...
```

### 测试

每个模块都应该有对应的测试文件：

```
deepeye/nodes/base.py  →  tests/nodes/test_base.py
```

## 下一步

按照上面的开发顺序建议，我们应该首先开发：

1. **节点系统基础** (`nodes/io/`, `nodes/base.py`, `nodes/registry.py`)
2. **工作流引擎** (`workflow/` 目录下的文件)
3. **执行运行时** (`runtime/` 目录下的文件)

准备好后，我们就可以开始编写代码了！

