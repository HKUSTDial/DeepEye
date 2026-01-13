
---

# 工作流执行引擎逻辑（中文版）

本文描述 `deepeye.workflows.engine` 的运行时执行逻辑。

## 目标

- 提供一套最小但可预测的 DAG 工作流执行引擎
- 严格区分定义态校验与运行态执行
- 通过 `node.type` 动态绑定执行处理器

## 核心组件

### 定义模型

- `Workflow` → 根 `Graph` 的容器
- `Graph` → 节点与连线（DAG）
- `Node` → 纯定义（端口、参数、策略、元数据）
- `Port` → 约束与类型，不承载数据

### 运行态模型

- `ExecutionContext` → 一次运行的上下文，包含所有 `NodeRun`
- `NodeRun` → 单节点运行状态（inputs/outputs/status/timestamps）

### 注册表

- `NodeRegistry` → 定义态的 `NodeSpec` 注册表（用于校验）
- `HandlerRegistry` → 运行态处理器注册表（`node.type` → `NodeHandler`）

## 执行流程

1. **（可选）校验**
   - `validate_workflow_graph` 检查：DAG、端口规则、Group 映射、schema 兼容性等
2. **初始化上下文**
   - 为每个节点预创建 `NodeRun`
3. **拓扑排序**
   - `_topological_sort` 确保先执行上游节点
4. **输入解析**
   - `_resolve_inputs` 从上游 `outputs` 组装输入
   - `multiple=true` 的端口汇总为数组
   - 若无输入则尝试 `default`，且 `required=true` 必须满足
5. **执行处理器**
   - 根据 `node.type` 调用已注册的 handler
   - 返回的输出写入 `NodeRun.outputs`
6. **结束**
   - 全部成功 → `ExecutionContext.status = success`
   - 任一失败 → `status = failed` 并提前终止

## 错误处理

- 处理器抛错即视为节点失败
- 引擎停止执行后续节点
- 错误信息写入 `NodeRun.error`

## 数据语义

- 数据只存在于运行态（`NodeRun`）
- 定义态对象不携带任何运行数据
- Port 仅描述规则，Edge 仅描述连接

## 示例运行

`deepeye.workflows.examples` 注册了节点与处理器，并运行：

- `wf_simple`（source → transform）
- `wf_group`（Group 映射示例）
- `wf_accuracy`（比较 → 准确率）

运行方式：

```
python -m deepeye.workflows.examples
```

## 示例：注册并运行一个 Workflow（中文）

```python
from typing import Any

from deepeye.workflows.engine import ExecutionEngine
from deepeye.workflows.models import Edge, EdgeEndpoint, Graph, Node, Port, Workflow
from deepeye.workflows.registry import NodeRegistry, NodeSpec


class ListSourceHandler:
    def execute(self, node: Node, inputs: dict[str, Any], context: object) -> dict[str, Any]:
        return {"items": node.params.get("items", [])}


class CompareHandler:
    def execute(self, node: Node, inputs: dict[str, Any], context: object) -> dict[str, Any]:
        preds = list(inputs.get("predictions", []))
        labels = list(inputs.get("labels", []))
        size = min(len(preds), len(labels))
        correct_flags = [preds[i] == labels[i] for i in range(size)]
        return {"correct_flags": correct_flags}


class AccuracyHandler:
    def execute(self, node: Node, inputs: dict[str, Any], context: object) -> dict[str, Any]:
        flags = list(inputs.get("correct_flags", []))
        accuracy = (sum(1 for f in flags if f) / len(flags)) if flags else 0.0
        return {"accuracy": accuracy}


# 1) 注册节点规范（定义态）
registry = NodeRegistry()
registry.register(NodeSpec(type="list_source", outputs={"items": Port(schema="list[bool]")}))
registry.register(
    NodeSpec(
        type="compare",
        inputs={
            "predictions": Port(schema="list[bool]", required=True),
            "labels": Port(schema="list[bool]", required=True),
        },
        outputs={"correct_flags": Port(schema="list[bool]")},
    )
)
registry.register(
    NodeSpec(
        type="accuracy",
        inputs={"correct_flags": Port(schema="list[bool]", required=True)},
        outputs={"accuracy": Port(schema="float")},
    )
)

# 2) 构建工作流图
nodes = {
    "labels": Node(
        id="labels",
        type="list_source",
        outputs={"items": Port(schema="list[bool]")},
        params={"items": [True, False, True, True, False]},
    ),
    "preds": Node(
        id="preds",
        type="list_source",
        outputs={"items": Port(schema="list[bool]")},
        params={"items": [True, True, True, False, False]},
    ),
    "compare": Node(
        id="compare",
        type="compare",
        inputs={
            "predictions": Port(schema="list[bool]", required=True),
            "labels": Port(schema="list[bool]", required=True),
        },
        outputs={"correct_flags": Port(schema="list[bool]")},
    ),
    "accuracy": Node(
        id="accuracy",
        type="accuracy",
        inputs={"correct_flags": Port(schema="list[bool]", required=True)},
        outputs={"accuracy": Port(schema="float")},
    ),
}
edges = {
    "e_labels": Edge(
        id="e_labels",
        source=EdgeEndpoint(node_id="labels", port_id="items"),
        target=EdgeEndpoint(node_id="compare", port_id="labels"),
    ),
    "e_preds": Edge(
        id="e_preds",
        source=EdgeEndpoint(node_id="preds", port_id="items"),
        target=EdgeEndpoint(node_id="compare", port_id="predictions"),
    ),
    "e_correct": Edge(
        id="e_correct",
        source=EdgeEndpoint(node_id="compare", port_id="correct_flags"),
        target=EdgeEndpoint(node_id="accuracy", port_id="correct_flags"),
    ),
}
workflow = Workflow(id="wf_accuracy", root=Graph(nodes=nodes, edges=edges))

# 3) 注册运行处理器并执行
engine = ExecutionEngine(node_registry=registry)
engine.register_handler("list_source", ListSourceHandler())
engine.register_handler("compare", CompareHandler())
engine.register_handler("accuracy", AccuracyHandler())

context = engine.run(workflow)
print(context.runs["accuracy"].outputs["accuracy"])
```

## 可扩展方向

- 根据 `Node.policy` 支持 retry/timeout/cache
- 支持 condition/transform 边语义
- 异步 handler
- 可并行执行的分支
