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

系统会自动发现 `packages/backend/app/node/` 目录下的节点。

## 目录结构

```
packages/backend/app/node/
  base.py                # BaseNode 抽象
  __init__.py            # 自动发现与注册
  utils.py               # 通用工具
  datasource_read.py     # 节点实现
  sql_execute.py         # 节点实现
  data_filter_rows.py    # 节点实现
  ...
```

## 节点声明规范

每个节点需要继承 `BaseNode` 并实现：

- `node_type`（字符串）
- `spec()` classmethod → 返回 `NodeSpec`
- `build_handler(db, user_id)` classmethod → 返回 `NodeHandler` 或 `None`

示例：

```python
from app.node.base import BaseNode
from deepeye.workflows.registry import NodeSpec
from deepeye.workflows.models import Port

class MyNode(BaseNode):
    node_type = "my.node"

    @classmethod
    def spec(cls) -> NodeSpec:
        return NodeSpec(
            type=cls.node_type,
            description="做一些有用的事情。",
            inputs={"rows": Port(schema="list[dict]", required=True)},
            outputs={"rows": Port(schema="list[dict]")},
            params_schema={
                "limit": {"type": "integer", "required": False, "description": "最大行数"},
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

- 自动导入 `app.node` 下所有模块
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
- 节点文件名与 type 对齐（snake_case）
- handler 逻辑单一、可测试

## 现有核心节点

Data:
- `datasource.read`
- `sql.execute`
- `data.select_columns`
- `data.filter_rows`
- `data.sort_rows`
- `data.limit_rows`
- `data.aggregate`

Stats:
- `stats.summary`
- `stats.correlation`

Viz:
当前移除了可视化节点。
