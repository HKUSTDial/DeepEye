# Workflow Node 系统说明（详细版）

## 作用
Workflow Node 系统负责：
1) 统一节点协议（inputs/outputs/params）  
2) 校验 workflow 结构  
3) 执行 DAG 并产出结果  

## 代码结构

### 1) NodeSpec / Registry
路径：`packages/core/deepeye/workflows/registry.py`  
核心类：
- `NodeSpec`：描述节点类型、端口、参数
- `NodeRegistry`：全局注册表

### 2) Node 实现与注册
路径：`packages/backend/app/node/*`  
关键点：
- `BaseNode` 在 `packages/backend/app/node/base.py`  
- `register_node_specs` 与 `register_node_handlers` 在 `packages/backend/app/node/__init__.py`  
- 通过扫描 `BaseNode` 子类自动注册  
- `_DISABLED_NODE_TYPES` 控制哪些节点会从系统中排除

### 3) Engine 与校验
路径：`packages/backend/app/services/workflow_engine.py`  
职责：
- 构建 `ExecutionEngine`
- 注册 Node handler
- 注册 condition/transform（always/identity）

执行入口：
`packages/backend/app/services/workflow_file_service.py`  
负责读取 workflow JSON → 校验 → 执行 → 发布事件

## 核心功能类说明

- `BaseNode`  
  - 必须实现 `spec()`  
  - 可选实现 `build_handler()`  

- `ExecutionEngine`  
  - 运行 DAG  
  - 提供 `on_node_start` / `on_node_end` hook  

- `WorkflowValidationError`  
  - 明确指出结构问题与端口错误  

## 扩展方式

### 新增一个 Node

示例：新增 “CSV 导出”节点  

1) 编写节点类
```python
# packages/backend/app/node/data_export_csv.py
from deepeye.workflows.registry import NodeSpec
from app.node.base import BaseNode
from deepeye.workflows.engine import NodeHandler

class DataExportCsv(BaseNode):
    node_type = "data.export_csv"

    @classmethod
    def spec(cls) -> NodeSpec:
        return NodeSpec(
            type=cls.node_type,
            description="Export rows to CSV file",
            inputs={"rows": {"schema": "list[dict]", "required": True， "multiple": True}},
            outputs={"path": {"schema": "string"}},
            params_schema={"filename": {"type": "string", "required": True}},
        )

    @classmethod
    def build_handler(cls, db, user_id, sandbox=None) -> NodeHandler | None:
        async def handler(inputs, params, context):
            filename = params.get("filename", "export.csv")
            rows = inputs.get("rows", [])
            # TODO: 写入 sandbox 文件
            return {"path": f"/workspace/{filename}"}

        return handler
```

2) 注册节点  
无需手动注册，`register_node_specs` 会扫描 `BaseNode` 子类。  
若有特殊排除，请确认 `_DISABLED_NODE_TYPES`。

3) 前端可见  
`/api/v1/workflow-nodes` 会自动返回新节点定义。

