
---

# Workflow System 抽象设计文档（精简版）

## 1. 设计目标

构建一套 **可组合、可校验、可执行、可扩展** 的 workflow 系统，满足：

* Workflow 是 **有向无环图（DAG）**
* Node 是基本执行单元
* 支持 **GroupNode（折叠节点）**，用于结构复用与分层编排
* **定义态（Definition）与运行态（Runtime）严格分离**
* 所有规则可被**机器读取**，以支持自动校验与文档生成

---

## 2. 核心设计原则（共识）

### 2.1 定义态 vs 运行态分离

* **Node / Graph / Edge / Port**：只描述“是什么、怎么连”
* **NodeRun / ExecutionContext**：描述“一次执行发生了什么”
* 定义态对象中 **不存任何运行时数据**

### 2.2 数据模型结论

* **数据存在于 NodeRun**
* **Port 只是接口与约束，不承载数据**
* **Edge 不存数据，只描述数据如何流动**

一句话总结：

> NodeRun 存数据，Port 管规则，Edge 负责搬运。

---

## 3. 顶层结构

### Workflow

* 作用：工作流的持久化与版本容器
* 只包含一个 `root Graph`

```text
Workflow
└── Graph (root)
```

---

## 4. Graph（图）

### 职责

* 描述一张单层 DAG
* 提供校验与拓扑排序能力

### 核心属性

* `nodes: Dict[node_id, Node]`
* `edges: Dict[edge_id, Edge]`

### 核心规则

* 无环（DAG）
* Edge 必须是 **output → input**
* input port 的 `required / multiple` 规则必须满足

---

## 5. Node（节点）

### 职责

* 描述一个执行单元或结构单元
* 不包含运行态

### 核心属性

* `id`
* `type`:

  * `task`：业务节点
  * `group`：折叠节点
  * `group_inputs` / `group_outputs`：Group 边界节点
* `inputs: Dict[port_id, Port]`
* `outputs: Dict[port_id, Port]`
* `params`: 节点参数（业务或结构）
* `policy`: **执行语义**（timeout / retry / cache 等）
* `metadata`: **UI / 组织信息**（位置、标签、注释等）
  * `position`: `{ x: number, y: number }`，用于记录画布坐标（以画布像素为单位）

### 设计取舍

* `policy` ≠ `metadata`

  * policy 会影响执行器行为
  * metadata 只影响展示与组织

---

## 6. Port（端口）

### 职责

* 定义接口契约与约束规则

### 核心属性

* `schema`: 类型（string / json / any / JSONSchema）
* `required`
* `multiple`
* `default`
* `examples / description`

### 重要约定

* **port_id 使用稳定字符串（如 text/json），不用 UUID**
* Port 中不存 value

---

## 7. Edge（连线）

### 职责

* 描述两个端口之间的连接关系

### 核心属性

* `source: (node_id, port_id)`
* `target: (node_id, port_id)`
* 可选：`condition / transform`（设计态）
  * `transform` 的输出必须满足 target input 的 schema

---

## 8. GroupNode（折叠节点设计）

### 核心思想

> GroupNode 是一个普通 Node，对外暴露 ports，对内携带一张 Graph。

### 结构

```text
Node(type="group")
├── inputs / outputs   ← 外部接口
└── params.graph       ← 内部 Graph
```

---

## 9. Group 边界节点（关键共识）

### 设计选择

采用 **多端口映射的边界节点**（而不是一个端口一个节点）

### GroupInputs

* 作用：把外部输入端口引入内部
* params：

```text
map: { external_in_port -> internal_out_port }（key 为外部 in port，value 为内部 out port）
```

### GroupOutputs

* 作用：把内部结果导出为外部输出
* params：

```text
map: { internal_in_port -> external_out_port }（key 为内部 in port，value 为外部 out port）
```

### 优点

* 支持多个输入/输出
* 不依赖 UUID 定位内部节点
* UI 与校验逻辑更清晰
* 映射只发生在“边界节点自身端口”

---

## 10. 运行态模型

### NodeRun

* 表示 **一次执行中某个节点的状态**
* 核心字段：

  * `inputs`
  * `outputs`
  * `status`
  * `error`

### ExecutionContext

* 表示一次 workflow run
* 持有所有 NodeRun

### 注册时机（共识）

* **在 workflow run 创建时，提前为所有 Node 初始化 NodeRun**
* 有利于调试、可视化、失败恢复

---

## 11. 执行逻辑放在哪里？

### 结论

* **不放在 Node 定义里**
* 放在 **NodeHandler / NodeExecutor / Registry** 中

```text
NodeDef  +  NodeSpec  →  NodeHandler.execute(...)
```

Node 只描述“是什么”，Handler 决定“怎么跑”。

---

## 12. 规则协议与自动文档（NodeSpec）

### 目标

让所有规则 **机器可读 → 自动生成文档**

### NodeSpec 应包含

* 节点类型 ID
* description（节点做什么）
* params 的 Pydantic / JSONSchema
* ports 定义（schema / required / examples）
* 额外规则（端口依赖、互斥等）

### 收益

* 自动校验
* 自动生成说明文档
* 统一节点实现规范
* 插件化扩展能力

---

## 13. 总结一句话

> **Graph 管结构，Node 管接口，Port 管规则，NodeRun 管数据，GroupNode 管复用，NodeSpec 管规范。**

---

## 14. 执行语义与校验补充（建议版）

以下约定用于闭环执行语义，避免实现分歧。

### 14.1 端口连线与合流规则

* `input.multiple=false`：只允许 1 条入边，超过即校验失败
* `input.multiple=true`：允许多入边，运行时 inputs 以数组形式聚合
* `input.required=true`：运行前必须满足至少 1 条有效输入（或 default）
* `input.default`：当没有任何输入时使用

### 14.2 Edge 条件与变换

* `condition` 为 false：该 Edge 视为未触发，不参与下游输入
* `transform` 失败：当前 NodeRun 失败，错误挂在 Edge 对应的输入路径
* `condition/transform` 必须是纯函数（无副作用）

### 14.3 NodeRun 写入时机

* 节点执行开始前：记录 `inputs` 和 `status=running`
* 执行完成：写入 `outputs` 并标记 `status=success`
* 执行失败：写入 `error` 并标记 `status=failed`
* 流式输出：允许追加 `outputs`，最终以 `status=success` 封口

### 14.4 失败传播与重试

* 节点失败后，下游默认不触发
* `policy.retry`：仅对当前节点重试，不影响上游
* `policy.timeout`：超时等同于失败
* `policy.cache`：命中时直接写入 outputs，跳过执行

### 14.5 GroupNode 约束

* GroupNode 的外部 `inputs/outputs` 必须由 GroupInputs/GroupOutputs 映射覆盖
* Group 内部 Graph 仍需满足 DAG 校验
* Group 边界节点仅作映射，不承载业务逻辑

### 14.6 版本与兼容性

* NodeSpec 变更需提升 `version`
* Workflow 保存时记录所有 NodeSpec 版本
* 执行器必须拒绝不兼容版本或提供迁移策略

### 14.7 校验清单（建议最小集合）

* Graph 无环
* 所有 Edge 均为 output -> input
* input.multiple=false 的入边数量 <= 1
* required input 在运行前可满足（或有 default）
* Group 映射覆盖外部端口
* Node type 必须存在于 Registry
