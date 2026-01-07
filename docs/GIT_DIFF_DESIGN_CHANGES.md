# 设计变更详解（基于 Git Diff）

本文档从 `git diff` 角度详细解释每个代码变更的设计意图。

---

## 1. 后端事件系统重构

### 1.1 `packages/backend/app/schemas/events.py`

**变更前：**
```python
class AgentEventType(str, Enum):
    """Event types for real-time streaming."""
    TOKEN = "token"
    TOOL_START = "tool_start"
    ...
```

**变更后：**
```python
class EventTypeBase(str, Enum):
    """Base class for all event types."""
    pass

class AgentEventType(EventTypeBase):
    """Agent-related event types."""
    ...

class SandboxEventType(EventTypeBase):
    """Sandbox-related event types."""
    STARTED = "sandbox_started"
    FILES_CHANGED = "sandbox_files_changed"
    ...
```

**设计意图：**
- 引入 `EventTypeBase` 基类，建立事件类型层次结构
- 新增 `SandboxEventType` 用于 Sandbox 相关事件
- `sandbox_started`: 通知前端打开文件面板
- `sandbox_files_changed`: 通知前端刷新目录

**为什么这样设计？**
- 解耦 Agent 事件和 Sandbox 事件，职责分离
- 前端可以统一处理 SSE 事件，根据 `type` 字段分发处理

---

## 2. Agent 任务流程变更

### 2.1 `packages/backend/app/tasks/agent_tasks.py`

**核心 Diff：**

```diff
-from app.schemas import AgentEvent, AgentEventType, AgentInput, UserMessage
+from app.sandbox.manager import SandboxManager
+from app.sandbox.tools import get_sandbox_tools
+from app.schemas import AgentEvent, AgentEventType, AgentInput, UserMessage, SandboxEvent, SandboxEventType
```

```diff
+    sandbox_manager = SandboxManager()
+    sandbox = await sandbox_manager.get_or_create_sandbox(session_id)
+    
+    # Notify frontend that sandbox is ready
+    await event_bus.publish(
+        channel, 
+        SandboxEvent(type=SandboxEventType.STARTED, source="sandbox").model_dump_json()
+    )
```

```diff
-    tools.append(create_code_agent_tool(settings.SANDBOX_URL, model, callbacks=[cb_code]))
+    sandbox_tools = get_sandbox_tools(sandbox, on_files_changed=on_files_changed)
+    tools.append(create_code_agent_tool(sandbox_tools, model, session_id, callbacks=[cb_code]))
```

**设计意图：**

| 变更点 | 原设计 | 新设计 | 原因 |
|--------|--------|--------|------|
| Sandbox 获取 | 每次创建新 sandbox | `get_or_create_sandbox` 复用现有 | 避免重复创建容器 |
| 工具创建 | 传 `sandbox_url` | 传 `sandbox_tools` + `session_id` | 直接注入已创建的 sandbox 工具 |
| 事件通知 | 无 | 发送 `STARTED` 和 `FILES_CHANGED` 事件 | 前端实时响应 |

**回调机制设计：**
```python
def on_files_changed():
    """命令执行成功后触发"""
    event = SandboxEvent(type=SandboxEventType.FILES_CHANGED, source="sandbox")
    asyncio.create_task(event_bus.publish(channel, event.model_dump_json()))
```

---

## 3. Sub-Agent 上下文保持

### 3.1 `packages/core/deepeye/tools/agent_tools.py`

**变更前：**
```python
def create_sql_agent_tool(db_uri: str, model: BaseChatModel, callbacks=None):
    ...
    @tool
    async def ask_database(question: str):
        sub_thread_id = f"sub_sql_{uuid.uuid4()}"  # 每次新 UUID
        ...
```

**变更后：**
```python
def create_sql_agent_tool(db_uri: str, model: BaseChatModel, session_id: str, callbacks=None):
    ...
    sub_thread_id = f"sql_agent_{session_id}"  # 基于 session 固定
    
    @tool
    async def ask_database(question: str):
        # 使用闭包捕获的固定 sub_thread_id
        ...
```

**设计意图：**

```
原设计: 每次调用 → 新 UUID → 无记忆
         
         调用1: sub_sql_abc123 → 执行 → 遗忘
         调用2: sub_sql_def456 → 执行 → 遗忘
         
新设计: 基于 session_id → 固定 thread_id → 有记忆

         调用1: sql_agent_session123 → 执行 → 保存状态
         调用2: sql_agent_session123 → 读取状态 → 继续执行
```

**同样适用于 Code Agent：**
```diff
-def create_code_agent_tool(sandbox_url: str, model: BaseChatModel, callbacks=None):
+def create_code_agent_tool(sandbox_tools: list, model: BaseChatModel, session_id: str, callbacks=None):
+    sub_thread_id = f"code_agent_{session_id}"
```

---

## 4. 前端事件响应机制

### 4.1 `packages/frontend/src/stores/chat.ts`

**新增状态：**
```diff
+  // File refresh trigger - increments when sandbox files change
+  const filesChangedTrigger = ref(0)
+  
+  // Sandbox started trigger - increments when sandbox starts
+  const sandboxStartedTrigger = ref(0)
```

**设计意图：**
- 使用 `ref(number)` 作为事件触发器
- 组件 `watch` 该值，当值变化时执行相应逻辑
- 简单递增操作，无需复杂的事件对象

### 4.2 `packages/frontend/src/composables/useChat.ts`

**新增事件处理：**
```diff
 es.onmessage = (event) => {
   const agentEvent: AgentEvent = JSON.parse(event.data)
   
+  // Handle sandbox events
+  if (agentEvent.type === 'sandbox_started') {
+    store.notifySandboxStarted()
+    return
+  }
+  if (agentEvent.type === 'sandbox_files_changed') {
+    store.notifyFilesChanged()
+    return
+  }
```

**设计意图：**
- SSE 统一入口处理所有事件类型
- 根据 `type` 字段分发到不同处理逻辑
- Sandbox 事件直接调用 store 方法，不参与消息构建

### 4.3 `packages/frontend/src/App.vue`

**自动打开文件面板：**
```diff
+watch(() => chatStore.sandboxStartedTrigger, () => {
+  if (chatStore.sandboxStartedTrigger > 0 && currentDataSourceId.value) {
+    const wasCollapsed = filesPanelCollapsed.value
+    filesPanelCollapsed.value = false
+    if (wasCollapsed) {
+      chatStore.notifyFilesChanged()  // 打开时触发刷新
+    }
+  }
+})
```

**设计流程：**
```
后端 sandbox 启动
       ↓
发送 SandboxEvent(STARTED)
       ↓
前端 SSE 收到事件
       ↓
store.notifySandboxStarted()
       ↓
sandboxStartedTrigger++
       ↓
App.vue watch 触发
       ↓
filesPanelCollapsed = false (打开面板)
       ↓
notifyFilesChanged() (刷新目录)
```

---

## 5. 会话标题自动更新

### 5.1 `packages/frontend/src/composables/useChat.ts`

**变更：**
```diff
+  // Check if this is the first message (for title update)
+  const isFirstMessage = store.messages.length === 0
+  
   store.startStreaming()
   store.addUserMessage(text)

   try {
     await chatApi.start({ ... })

+    // Update session title with first message content
+    if (isFirstMessage) {
+      const title = text.length > 50 ? text.substring(0, 47) + '...' : text
+      await store.updateSessionTitle(session_id, title)
+    }
```

**设计意图：**
- 仅在首条消息时更新标题
- 截断过长文本（>50 字符）
- 调用后端 API 持久化标题

### 5.2 `packages/frontend/src/components/Sidebar.vue`

**打字动画效果：**
```javascript
// 检测标题变化并触发动画
watch(displaySession, (newVal, oldVal) => {
  if (oldVal?.title === 'New conversation' && 
      newVal?.title !== 'New conversation') {
    // 触发打字动画
    startTypingAnimation(newVal.title)
  }
})
```

---

## 6. 数据流总览

```
用户发送消息
    │
    ▼
前端 useChat.sendMessage()
    │
    ├─► 检测 isFirstMessage
    │
    ▼
后端 /chat/start
    │
    ▼
Celery Task: agent_tasks.run_agent_workflow
    │
    ├─► SandboxManager.get_or_create_sandbox()
    │       │
    │       └─► 查找现有容器 或 创建新容器
    │
    ├─► 发送 SandboxEvent(STARTED) ─────────────────►  前端打开文件面板
    │
    ├─► 创建 sandbox_tools (with on_files_changed 回调)
    │
    ├─► create_code_agent_tool(sandbox_tools, session_id)
    │       │
    │       └─► 使用固定 thread_id: f"code_agent_{session_id}"
    │
    ▼
Agent 执行
    │
    ├─► 执行 bash 命令
    │       │
    │       └─► on_files_changed() ─────────────────►  前端刷新目录
    │
    └─► 返回结果

前端收到 agent_end
    │
    ├─► isFirstMessage? ─► 更新会话标题 ─► 打字动画
    │
    └─► 完成
```

---

## 7. 关键设计决策

| 决策 | 选择 | 备选方案 | 选择原因 |
|------|------|----------|----------|
| 事件触发机制 | `ref(number)` 递增 | EventEmitter / Vuex Actions | 简单直观，Vue 原生支持 |
| Sub-Agent 记忆 | 固定 `thread_id` | 传递历史消息 | 利用 LangGraph 内置 checkpointer |
| Sandbox 复用 | `get_or_create_sandbox` | 缓存 URL | 直接复用容器实例，避免 URL 解析 |
| 标题更新时机 | 首条消息后 | 每条消息摘要 | 简单明确，用户意图清晰 |
| 目录刷新策略 | 事件驱动 | 轮询 | 实时性好，资源消耗低 |

---

## 8. 文件变更清单

```bash
# 后端变更
packages/backend/app/schemas/events.py        # 新增 SandboxEventType
packages/backend/app/tasks/agent_tasks.py     # Sandbox 集成 + 事件发送

# Core 变更
packages/core/deepeye/tools/agent_tools.py    # session_id 参数 + 固定 thread_id

# 前端变更
packages/frontend/src/stores/chat.ts          # 新增 trigger refs
packages/frontend/src/composables/useChat.ts  # 事件处理 + 标题更新
packages/frontend/src/App.vue                 # watch 自动打开面板
packages/frontend/src/components/Sidebar.vue  # 打字动画
```

