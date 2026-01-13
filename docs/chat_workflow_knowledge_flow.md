# 用户消息到 Workflow / Knowledge 的全流程（含代码路径）

本文档描述“用户发送一条消息”到 Workflow 与 Knowledge 交互的完整链路，并标注具体源码位置。

## 1. 前端：用户发送消息

**入口组件**
- `packages/frontend-react/src/components/ChatBox.tsx`
  - `handleSend()` 调用 `useChat.sendMessage(...)`
  - 如果输入包含 `@知识库名称`，会提取对应 `kb_ids`

**请求发送**
- `packages/frontend-react/src/hooks/useChat.ts`
  - `sendMessage(text, datasourceId, kbIds)`
  - 调用 `chatApi.start(...)`

**API 调用**
- `packages/frontend-react/src/api/chat.ts`
  - `POST /api/v1/chat`  
  - 请求体包含：`message / session_id / datasource_id / kb_ids`

## 2. 后端：Chat API 入口

**路由入口**
- `packages/backend/app/api/v1/chat.py`
  - `start_chat()` 接收请求并调用：
    - `start_agent_workflow(session_id, message, datasource_id, kb_ids)`

**任务分发**
- `packages/backend/app/services/chat_service.py`
  - `start_agent_workflow(...)`
  - 把 `AgentInput` 丢给 Celery：`run_agent_workflow.delay(...)`

**请求数据结构**
- `packages/backend/app/schemas/api.py` → `ChatRequest`
- `packages/backend/app/schemas/input.py` → `AgentInput`（含 kb_ids）

## 3. 后端：Agent 任务执行（核心链路）

**任务入口**
- `packages/backend/app/tasks/agent_tasks.py`
  - `run_agent_workflow()` → `_run_agent_async()`

**执行步骤**
1) 创建模型  
   - `_create_model()`（OpenAI Chat 模型配置）
2) 创建回调与事件收集器  
   - `AgentCallback` / `MessageCollector`  
   - 代码：`packages/backend/app/tasks/callbacks.py`
3) 创建 / 复用 Sandbox  
   - `SandboxManager.get_or_create_sandbox()`  
   - 代码：`packages/backend/app/sandbox/manager.py`
4) 构建工具列表  
   - Workflow 相关工具：  
     - `create_design_workflow_tool`  
     - `create_run_workflow_from_file_tool`
   - Knowledge 相关工具：  
     - `create_knowledge_base_agent_tool`（当 kb_ids 存在时注入）
   - 代码：`packages/backend/app/tools/workflow_tools.py`  
   - 代码：`packages/backend/app/tools/kb_tools.py`
5) Supervisor 执行  
   - `SupervisorAgent` 根据提示词选择工具  
   - 代码：`packages/core/deepeye/agents/supervisor.py`

## 4. Knowledge 交互流程（KB Agent）

**触发条件**
- Supervisor 检测到 @知识库 或知识库查询类问题  
  - 提示词：`packages/core/deepeye/agents/supervisor.py`

**KB Agent 工具**
- `query_knowledge_base`（tool）
  - 实际调用 `KnowledgeBaseAgent`
  - 代码：`packages/backend/app/tools/kb_tools.py`

**KB Agent 执行**
- `KnowledgeBaseAgent` 运行 ReAct 循环  
  - 代码：`packages/core/deepeye/agents/knowledge_base_agent.py`
  - 强制调用 `execute_kb_sql`

**SQL 检索工具**
- `execute_kb_sql`（tool）
  - 仅允许 SELECT
  - 必须包含 `:user_id` 与 `:kb_ids`
  - 代码：`packages/backend/app/tools/kb_tools.py`

## 5. Workflow 交互流程（Workflow Agent）

**触发条件**
- Supervisor 判断需要 workflow 执行（分析/图表/文件生成）

**Workflow Agent 工具**
- `design_workflow`（tool）  
  - 代码：`packages/backend/app/tools/workflow_tools.py`

**Workflow Agent 执行**
- `WorkflowAgent` 生成 workflow JSON  
  - 提示词：`packages/backend/app/services/workflow_prompts.py`
  - Agent：`packages/core/deepeye/agents/workflow_agent.py`

**创建/更新 workflow**
- `create_workflow` / `update_workflow`  
  - 写入 `/workspace/workflow/*.json`
  - 代码：`packages/backend/app/tools/workflow_tools.py`

**运行 workflow**
- `run_workflow_from_file`  
  - 代码：`packages/backend/app/services/workflow_file_service.py`

## 6. Workflow 执行引擎

**引擎创建**
- `build_engine()`  
  - 代码：`packages/backend/app/services/workflow_engine.py`

**Node 注册**
- `register_node_specs / register_node_handlers`  
  - 代码：`packages/backend/app/node/__init__.py`

**执行**
- `ExecutionEngine.run(...)`  
  - 代码：`packages/core/deepeye/workflows/engine.py`

## 7. 事件推送与前端渲染

**后端事件发布**
- `AgentCallback` → `workflow_event`
  - 代码：`packages/backend/app/tasks/callbacks.py`
- `workflow_file_service` → `run_start / node_status / run_end`
  - 代码：`packages/backend/app/services/workflow_file_service.py`

**前端消费**
- Chat SSE  
  - `packages/frontend-react/src/hooks/useChat.ts`
- LivePanel SSE  
  - `packages/frontend-react/src/components/right-panel/plugins/WorkflowLivePanel.tsx`

**渲染流程**
- `workflow_event(create/update)` → 渲染节点/连线  
- `node_status` → 更新节点状态  
- `run_end` → 输出结果  

## 8. 总结

从用户输入到最终输出，链路分为：
前端发送 → 后端调度 → Supervisor 决策 → KB / Workflow 执行 → SSE 事件 → 前端渲染。  
每个步骤都可通过对应源码追踪与扩展。  
