# RFC: Workflow-Native Agent 重构方案

状态: Accepted for implementation

作者: Codex

日期: 2026-03-06

关联文档:
- `docs/chat_workflow_knowledge_flow.md`
- `docs/workflow_node_system.md`
- `docs/panel_system.md`

## 1. 背景

当前系统已经具备以下基础能力:
- 用户通过 chat 提出问题
- 用户可以上传文件、连接数据库、引用知识库
- 后端存在 `Supervisor -> WorkflowAgent -> Workflow Engine` 主链路
- 前端 workspace 可以展示 files / workflow / report / dashboard / video preview

但当前实现仍然偏向:
- `chat-native product + workflow execution shell`

而不是目标中的:
- `workflow-native agent system`

也就是说，workflow 目前更多承担“部分执行容器”的角色，而不是系统内统一的规划与执行抽象。

本 RFC 的目标，是把系统收敛为下面这条标准主链路:

```text
用户提出需求
-> 配置当前会话相关数据源
-> Agent 判断是否需要工作流
-> Agent 基于标准 nodes 规划工作流
-> Validator 校验工作流
-> Executor 执行工作流
-> 产出标准化 artifacts / outputs
-> Assistant 基于真实执行结果回复
-> Workspace 展示完整过程和产物
```

## 2. 问题陈述

当前设计与目标态存在以下偏移:

1. `Supervisor` 更像路由器，而不是真正的 workflow orchestration 层。
2. `WorkflowAgent` 主要依赖长 prompt 和案例硬编码，不够通用、稳定。
3. `report/dashboard/video` 虽然是 nodes，但前后端都有专门旁路逻辑。
4. `workflow file path` 被当作事实主键，导致前端和执行链路高度耦合。
5. node spec 不是唯一事实源，validator / runtime / frontend editor 的契约没有严格收敛。
6. 事件协议不统一，前端需要对 report/video/dashboard 做大量特判。
7. datasource 当前更偏“用户全局可见”，而不是“当前 session/task 作用域”。

## 3. 目标

本次重构要达成以下目标:

1. 对于所有非简单回答类请求，workflow 成为默认执行抽象。
2. datasource attachment 明确为 session-scoped。
3. workflow draft / run / artifact 成为后端一等实体，不再由 sandbox 文件承担主真相。
4. node spec 成为唯一事实源，驱动 planner、validator、runtime、editor。
5. 所有 artifact 型能力统一走 workflow node，不再引入私有通道。
6. 统一事件协议，前端通过通用状态机渲染，而不是按节点类型分支判断。
7. Agent prompt 拆层，职责清晰，便于测试与迭代。

## 4. 非目标

以下事项不在本次重构的直接范围内:

1. 不改变当前 UI 的总体布局和视觉风格。
2. 不立即废弃 sandbox 文件系统，它仍会作为执行与导出介质存在。
3. 不一次性重写所有现有 node 的内部业务逻辑。
4. 不追求在第一阶段实现完整的自动 workflow 自修复闭环。

## 5. 设计原则

1. Single source of truth
   - node contract、workflow draft、workflow run、artifact metadata 都必须有明确主真相。

2. Workflow first
   - 简单问答可 direct answer，复杂任务必须进入 workflow lifecycle。

3. Session-scoped context
   - 数据源、运行状态、artifact 显示都围绕 session/turn，而不是围绕用户全局资源。

4. Contract over convention
   - 不允许靠 `file_path includes "data_video"`、`dashboard_url exists` 这类启发式驱动 UI。

5. Recoverable state
   - 页面刷新后，chat/workspace/artifact 状态应能从后端恢复，而不是依赖 SSE 临时事件重放。

## 6. 目标系统架构

### 6.1 顶层链路

```text
Chat UI
-> Session Attachments
-> Chat Turn
-> Supervisor
-> Workflow Planner
-> Workflow Validator
-> Workflow Repair Loop
-> Workflow Executor
-> Artifact Extractor
-> Run Summarizer
-> Workspace + Assistant Response
```

### 6.2 核心模块

#### Chat UI
- 只负责收集用户输入和显示过程
- 不再内嵌 workflow 私有逻辑

#### Session Attachment Service
- 管理当前 session 已附加的数据源
- 提供 planner 可消费的数据上下文

#### Supervisor
- 只负责决策
- 决定:
  - direct answer
  - ask for clarification
  - ask for data
  - run workflow

#### Workflow Planner
- 输入:
  - 用户目标
  - session attachments
  - node catalog summary
  - 历史 turn 摘要
- 输出:
  - 结构化 workflow draft

#### Workflow Validator
- 使用 node spec 和 schema rules 校验 draft
- 失败则返回结构化 validation issues

#### Workflow Repair Loop
- 将 validation issue 反馈给 planner/repair agent
- 最多有限次修复

#### Workflow Executor
- 只负责执行通过校验的 workflow
- 发布标准化节点生命周期事件

#### Artifact Extractor
- 从 node outputs 中提取统一 artifact
- artifact 类型包括:
  - `report`
  - `dashboard`
  - `video`
  - `file`
  - `table`
  - `text`

#### Run Summarizer
- 基于真实 run outputs / artifacts 总结回答
- 禁止在 workflow 未执行完成前生成“已完成”式回答

## 7. 领域模型重构

建议新增以下一等实体:

### 7.1 SessionAttachment

表示当前 session 附加的数据源引用。

建议字段:
- `id`
- `session_id`
- `datasource_id`
- `attached_at`
- `display_order`
- `metadata`

语义:
- attachment 是会话级上下文
- 用户删除 attachment，不影响 datasource 全局资源本体

### 7.2 ChatTurn

表示一次用户输入驱动的一轮处理过程。

建议字段:
- `id`
- `session_id`
- `user_message_id`
- `status`: `pending | planning | validating | running | summarizing | completed | failed`
- `intent_type`
- `created_at`
- `finished_at`

### 7.3 WorkflowDraft

表示某个 turn 生成的 workflow 定义版本。

建议字段:
- `id`
- `turn_id`
- `version`
- `definition`
- `planner_summary`
- `validation_status`
- `validation_errors`
- `created_at`

### 7.4 WorkflowRun

表示某个 draft 的执行记录。

建议字段:
- `id`
- `draft_id`
- `status`
- `started_at`
- `finished_at`
- `result_summary`
- `error`

### 7.5 WorkflowArtifact

表示 workflow 产出的标准化结果对象。

建议字段:
- `id`
- `run_id`
- `node_id`
- `kind`
- `title`
- `uri`
- `mime_type`
- `metadata`
- `created_at`

## 8. 工作流生命周期

标准生命周期定义为:

1. 创建 `ChatTurn`
2. `Supervisor` 做决策
3. 若需要 workflow:
   - 生成 `WorkflowDraft`
   - 执行 validation
   - 必要时进入 repair loop
4. draft 通过后创建 `WorkflowRun`
5. 执行节点
6. 提取 artifacts
7. 生成 assistant 总结
8. turn 完成

状态机:

```text
pending
-> planning
-> validating
-> running
-> summarizing
-> completed

或

planning/validating/running
-> failed
```

## 9. API 重构建议

### 9.1 Chat API

当前:
- `POST /api/v1/chat`

目标:
- `POST /api/v1/chat/turns`
  - 请求:
    - `session_id`
    - `message`
  - 响应:
    - `turn_id`
    - `session_id`
    - `status`

### 9.2 Session Attachments API

新增:
- `GET /api/v1/sessions/{session_id}/attachments`
- `POST /api/v1/sessions/{session_id}/attachments`
- `DELETE /api/v1/sessions/{session_id}/attachments/{attachment_id}`

### 9.3 Workspace State API

新增:
- `GET /api/v1/sessions/{session_id}/workspace-state`

返回:
- active turn
- latest draft
- latest run
- node states
- artifacts

### 9.4 Workflow Draft API

新增:
- `GET /api/v1/workflow-drafts/{draft_id}`
- `POST /api/v1/workflow-drafts/{draft_id}/execute`
- `POST /api/v1/workflow-drafts/{draft_id}/repair`

## 10. 统一事件协议

所有实时状态统一为 `workflow_event`。

### 10.1 顶层结构

```json
{
  "type": "workflow_event",
  "source": "workflow",
  "data": {
    "session_id": "uuid",
    "turn_id": "uuid",
    "draft_id": "uuid",
    "run_id": "uuid",
    "phase": "node_started",
    "payload": {}
  }
}
```

### 10.2 phase 列表

- `turn_started`
- `draft_created`
- `draft_updated`
- `validation_failed`
- `validation_passed`
- `run_started`
- `node_started`
- `node_log`
- `node_finished`
- `artifact_ready`
- `run_finished`
- `turn_finished`
- `turn_failed`

### 10.3 约束

1. 不再为 report 使用 `report_step` / `report_done`
2. 不再通过普通 token 传 dashboard 内部进度
3. 不再通过 `file_path` 推断 workflow 类型
4. artifact 的消费必须依赖 `artifact.kind`

## 11. Node Contract 统一规范

## 11.1 总体规则

1. `params`
   - 用于静态配置和用户文字约束
   - 例如:
     - `datasource_id`
     - `query`
     - `template`
     - `language`

2. `inputs`
   - 仅表示上游节点传入数据

3. `outputs`
   - handler 返回值中必须全部提前声明
   - 不允许 runtime 返回 spec 未声明字段

4. `metadata`
   - 只存 UI 和调试信息
   - 不参与业务执行语义

### 11.2 NodeSpec 增强字段

建议 `NodeSpec` 至少包含:
- `type`
- `version`
- `description`
- `params_schema`
- `inputs`
- `outputs`
- `artifact_schema`
- `examples`

### 11.3 Runtime 返回格式

长期建议统一为:

```python
{
  "outputs": {...},
  "artifacts": [...],
  "logs": [...]
}
```

短期兼容期:
- 仍允许 handler 直接返回 outputs dict
- 但 executor 层要统一归一化成标准结构

### 11.4 Validator 强化要求

validator 需要真正检查:
- node type 是否存在
- source/target port 是否存在
- required input 是否满足
- multiple 规则是否满足
- schema 是否兼容
- params 类型与 required 规则是否满足
- runtime outputs 是否只包含 spec 声明字段

## 12. Node 分层建议

### 12.1 Source Nodes
- `datasource.read`

### 12.2 Transform Nodes
- `rows.profile`
- `rows.select`
- `rows.filter`
- `rows.aggregate`
- `rows.sort`
- `rows.join`

### 12.3 Analysis Nodes
- `sql.execute`
- `python.code`

### 12.4 Artifact Nodes
- `report.generate`
- `data.generate_dashboard`
- `video.generator`

### 12.5 Answer Nodes
- `llm.answer`

`llm.answer` 的目的:
- 让“根据 workflow 执行结果回答用户问题”也成为 workflow 内部的显式一步
- 避免所有最终总结都发生在 workflow 外部

## 13. Agent 分层与 Prompt 设计

不再维持“一份超长 prompt 包办所有行为”的模式。

### 13.1 Supervisor Prompt

职责:
- 判断任务是否需要 workflow
- 判断是否需要补充信息
- 判断是否缺少数据

不负责:
- 具体 node wiring
- workflow JSON 细节

### 13.2 Workflow Planner Prompt

职责:
- 基于 node catalog 与 session context 生成 workflow draft

输入:
- 用户目标
- session attachments
- node catalog summary
- 常见编排模板

输出:
- workflow draft

### 13.3 Workflow Repair Prompt

职责:
- 根据 validator 错误修复 draft

输入:
- invalid workflow
- validation issues

输出:
- repaired workflow draft

### 13.4 Run Summarizer Prompt

职责:
- 根据真实 outputs / artifacts 组织最终回复

输入:
- 用户问题
- run outputs
- artifact summary
- failure info

输出:
- concise assistant answer

### 13.5 Prompt 规则

1. Prompt 中不要重复硬编码整套 node contract。
2. 优先通过 machine-readable catalog 提供约束。
3. video/report/dashboard 只给 pattern example，不给僵硬特例通道。
4. 所有 prompt 统一由 backend 侧构造，避免 core/backend 双份漂移。

## 14. 前端状态模型重构

### 14.1 Chat Store

负责:
- session list
- current session
- chat messages
- turn states

### 14.2 Attachment Store

负责:
- session attachments
- attachment CRUD

### 14.3 Workspace Store

负责:
- active turn
- workflow draft
- workflow run
- node states
- artifacts

### 14.4 前端原则

1. `sendMessage()` 只发 `session_id + text`
2. datasource attachment 不在每次 send 时重复拼装成“隐式请求参数”
3. workspace 从 `turn/run/artifact` 渲染
4. 页面刷新后通过 `workspace-state` 恢复
5. 不再根据特殊字段做 report/video/dashboard 分支判断

## 15. 迁移计划

### Phase 0: RFC

目标:
- 明确目标架构、契约、迁移阶段

产出:
- 本 RFC

### Phase 1: Session Attachments

目标:
- 将 datasource 使用模式从 user-global 改为 session-scoped attachment

主要工作:
- 新增 attachment 表和 API
- 前端 chat composer 改为 attachment 驱动

### Phase 2: Unified Workflow Event Contract

目标:
- 建立单一 `workflow_event` 协议

主要工作:
- report/dashboard/video 迁移到统一 phase
- 前端去除大部分节点私有特判

### Phase 3: Node Spec & Validation Hardening

目标:
- 让 node spec 成为唯一事实源

主要工作:
- 修正 validator
- 修正 API 输出
- 收紧 runtime outputs

### Phase 4: Turn / Draft / Run / Artifact 主链路

目标:
- 建立 workflow-native 的主状态模型

主要工作:
- 新增 turn/draft/run/artifact 持久化
- workflow file 从主真相降级为调试导出

### Phase 5: Agent Orchestration Refactor

目标:
- 引入真正的 `Supervisor -> Planner -> Repair -> Executor -> Summarizer`

### Phase 6: Frontend Workspace Binding

目标:
- 前端改为绑定 turn/run/artifact，而不是 file_path / 特殊事件

### Phase 7: Cleanup

目标:
- 清理旧 prompt、旧事件、旧 heuristic、旧 workflow file 主链路

## 16. 分支策略

集成分支:
- `refactor/workflow-native-agent`

后续阶段建议子分支:
- `feat/session-attachments-context`
- `refactor/unified-workflow-events`
- `refactor/node-spec-validation-contract`
- `refactor/turn-draft-run-artifact-model`
- `refactor/agent-workflow-orchestrator`
- `refactor/frontend-workspace-binding`
- `test/workflow-golden-scenarios`

合并规则:
1. 每个阶段单独 PR
2. 先合入集成分支
3. 集成联调与回归通过后，再合回 `master`

## 17. 测试策略

### 17.1 Core
- workflow engine tests
- validation tests

### 17.2 Backend Contract
- node registry response tests
- workflow validator tests
- event contract tests
- attachment scoping tests
- turn/draft/run/artifact persistence tests

### 17.3 Golden Scenarios

至少覆盖:
1. 无数据源时 ask for data
2. 文件数据 profile
3. 数据库 SQL 查询
4. report generation
5. dashboard generation
6. video generation
7. clarification path

### 17.4 Frontend
- 当前没有成熟 UI test 框架时，至少补:
  - workspace state recovery manual checklist
  - event replay manual checklist
  - artifact rendering manual checklist

## 18. 验收标准

以下条件全部满足，才算本次重构完成:

1. 用户附加数据到当前 session 后，不必每轮重复选择。
2. 非简单分析请求默认都有可见 workflow draft / run。
3. workflow 必须通过 validator 才能执行。
4. report/dashboard/video/file/table/text 都统一作为 artifact 展示。
5. assistant 最终回答必须基于真实执行结果。
6. 页面刷新后能恢复 turn / run / artifacts。
7. 前端不再依赖节点私有事件或文件名 heuristic。
8. prompt 只有一套真实生效来源。

## 19. 风险

1. 迁移期间新旧事件协议并存，前端兼容层容易变复杂。
2. node spec 收紧后，历史 workflow JSON 可能暴露出大量不规范定义。
3. 将 datasource 改为 session-scoped 后，现有“全局默认可用”的隐式行为会变化。
4. 引入 turn/draft/run/artifact 持久化后，后端数据模型和查询路径会明显增多。

## 20. 实施起点

本 RFC 通过后，下一步默认进入:
- `Phase 1: Session Attachments`

在进入编码前，需要先补一份 implementation checklist，明确:
- 数据库 schema 变更
- API 兼容策略
- 前端 store 拆分策略
- 回滚方案
