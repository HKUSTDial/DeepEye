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

The system automatically discovers all nodes under `packages/backend/app/node/`.

## Directory Layout

```
packages/backend/app/node/
  base.py                # BaseNode abstract class
  __init__.py            # auto-discovery + registry
  utils.py               # shared helpers
  datasource_read.py     # node implementation
  sql_execute.py         # node implementation
  data_filter_rows.py    # node implementation
  ...
```

## Node Declaration Contract

Every node is a class that inherits `BaseNode` and defines:

- `node_type` (string)
- `spec()` classmethod that returns `NodeSpec`
- `build_handler(db, user_id)` classmethod that returns `NodeHandler` or `None`

Example skeleton:

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
            description="Do something useful.",
            inputs={"rows": Port(schema="list[dict]", required=True)},
            outputs={"rows": Port(schema="list[dict]")},
            params_schema={
                "limit": {"type": "integer", "required": False, "description": "Max rows"},
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

- Imports all modules under `app.node`
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
- Node file names mirror node type (snake_case)
- Handlers are small and single-purpose

## Current Core Nodes

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
Visualization nodes are currently removed.
