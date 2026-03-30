# 工作流节点系统（中文）

本文说明当前 workflow 设计、节点声明规范与注册方式。

## 架构概览

工作流分为两层：

1) 定义层（NodeSpec）
- 描述节点是什么：type / inputs / outputs / params
- 用于校验和生成 AI 提示词

2) 执行层（NodeHandler）
- 节点运行时逻辑实现
- 通过 node type 注册到 ExecutionEngine

系统会通过 `packages/backend/app/node/__init__.py` 中的显式模块列表加载标准节点。

## 目录结构

```
packages/backend/app/node/
  core/
    base.py              # BaseNode 抽象
    db_utils.py          # 数据库通用工具
  data/
    datasource_read.py   # datasource.read 节点
    sql_execute.py       # sql.execute 节点
  code/
    python_code.py       # python.code 节点
  dashboard/
    node.py              # data.generate_dashboard 节点
    nl2dashboard/        # dashboard 生成内部实现
  report/
    node.py              # report.generate 节点
    runtime.py           # report 运行时编排
    report_module/       # report 生成内部实现
  video/
    node.py              # video.generator 节点
    config/              # 视频配置生成内部实现
    render/              # TSX 渲染流水线内部实现
  __init__.py            # 自动发现与注册
  ...
```

## 节点声明规范

每个节点需要继承 `BaseNode` 并实现：

- `node_type`（字符串）
- `spec()` classmethod → 返回 `NodeSpec`
- `build_handler(db, user_id)` classmethod → 返回 `NodeHandler` 或 `None`

示例：

```python
from app.node.core.base import BaseNode
from deepeye.workflows.registry import NodeSpec
from deepeye.workflows.models import Port

class MyNode(BaseNode):
    node_type = "my.node"

    @classmethod
    def spec(cls) -> NodeSpec:
        return NodeSpec(
            type=cls.node_type,
            description="做一些有用的事情。",
            inputs={"dataset_ref": Port(schema="dict", required=True)},
            outputs={
                "dataset_ref": Port(schema="dict", required=True),
                "preview_rows": Port(schema="list[dict]"),
                "row_count": Port(schema="int"),
                "columns": Port(schema="list[string]"),
            },
            params_schema={
                "limit": {"type": "integer", "required": False, "description": "预览行数上限"},
            },
        )

    @classmethod
    def build_handler(cls, db, user_id):
        return MyNodeHandler()
```

## 仅定义节点

如果某个节点只有定义而无需运行实现（如 group），可以让 `build_handler` 返回 `None`。
该节点仍会出现在 NodeSpec 注册表中。

## 自动发现与注册

`packages/backend/app/node/__init__.py`：

- 按显式配置导入节点模块
- 收集所有 `BaseNode` 子类
- 调用 `spec()` 注册 NodeSpec
- 调用 `build_handler(...)` 注册执行逻辑（如存在）

`packages/backend/app/services/workflow_engine.py`：

```python
registry = NodeRegistry()
register_node_specs(registry)

engine = ExecutionEngine(node_registry=registry)
register_node_handlers(engine, db, user_id)
```

## 提示词生成

workflow agent 的提示词由 NodeSpec 自动生成，确保 AI 只使用已注册节点。
提示词构建逻辑见：

- `packages/backend/app/services/workflow_prompts.py`

## 命名规范

- node type 用命名空间：`data.*` / `stats.*` / `datasource.*`
- 领域包统一使用 `node.py` 作为节点入口，内部实现放在子目录
- handler 逻辑单一、可测试
- 节点之间传递表格数据时，统一使用 `dataset_ref`。`preview_rows` 仅用于界面展示和摘要。
- `datasource.read` 只用于已附加的文件数据源。
- `sql.execute` 只用于已附加的数据库数据源。

## 现有核心节点

Data:
- `datasource.read`
- `sql.execute`
- `rows.select`
- `rows.filter`
- `rows.sort`
- `rows.aggregate`
- `rows.profile`
- `python.code`
- `report.generate`
- `data.generate_dashboard`
- `video.generator`
- `llm.answer`
