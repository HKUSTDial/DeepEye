# Workflow Node System

This document describes the current workflow design, node registration flow, and declaration conventions.

## Architecture Overview

The workflow system has two distinct layers:

1) Definition layer (NodeSpec)
- Describes what a node is: type, inputs, outputs, params.
- Used for validation and for generating AI prompts.

2) Execution layer (NodeHandler)
- Implements how a node runs at runtime.
- Registered in the ExecutionEngine by node type.

The system loads standard node modules from an explicit list in `packages/backend/app/node/__init__.py`.

## Directory Layout

```
packages/backend/app/node/
  core/
    base.py              # BaseNode abstract class
    db_utils.py          # shared DB helpers
  data/
    datasource_read.py   # datasource.read node
    sql_execute.py       # sql.execute node
  code/
    python_code.py       # python.code node
  dashboard/
    node.py              # data.generate_dashboard node
    nl2dashboard/        # dashboard generation internals
  report/
    node.py              # report.generate node
    runtime.py           # report runtime pipeline orchestration
    report_module/       # report generation internals
  video/
    node.py              # video.generator node
    config/              # video configuration generation internals
    render/              # TSX rendering pipeline internals
  __init__.py            # auto-discovery + registry
  ...
```

## Node Declaration Contract

Every node is a class that inherits `BaseNode` and defines:

- `node_type` (string)
- `spec()` classmethod that returns `NodeSpec`
- `build_handler(db, user_id)` classmethod that returns `NodeHandler` or `None`

Example skeleton:

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
            description="Do something useful.",
            inputs={"dataset_ref": Port(schema="dict", required=True)},
            outputs={
                "dataset_ref": Port(schema="dict", required=True),
            },
            params_schema={
                "limit": {"type": "integer", "required": False, "description": "Preview row limit"},
            },
        )

    @classmethod
    def build_handler(cls, db, user_id):
        return MyNodeHandler()
```

## Spec-Only Nodes

If a node is purely declarative (for UI or composition) and has no runtime handler,
return `None` from `build_handler`. The registry will still include its NodeSpec.

## Auto-Discovery and Registration

`packages/backend/app/node/__init__.py`:

- Imports an explicit list of node modules
- Collects all subclasses of `BaseNode`
- Registers specs via `node_cls.spec()`
- Registers handlers via `node_cls.build_handler(...)` when present

`packages/backend/app/services/workflow_engine.py` uses these hooks:

```python
registry = NodeRegistry()
register_node_specs(registry)

engine = ExecutionEngine(node_registry=registry)
register_node_handlers(engine, db, user_id)
```

## Prompt Generation

The workflow agent prompt is generated from registered `NodeSpec`s to keep AI behavior aligned with
actual capabilities. The prompt builder lives in:

- `packages/backend/app/services/workflow_prompts.py`

This ensures any new node automatically appears in the AI prompt.

## Naming Conventions

- Node type strings are namespaced: `data.*`, `stats.*`, `datasource.*`
- Domain packages use `node.py` as the node entrypoint, and keep internals under subpackages
- Handlers are small and single-purpose
- Use `dataset_ref` as the primary tabular data edge between nodes. `preview_rows` is only for UI and summaries.
- `datasource.read` is for attached file datasources only.
- `sql.execute` is for attached database datasources only.

## Current Core Nodes

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
