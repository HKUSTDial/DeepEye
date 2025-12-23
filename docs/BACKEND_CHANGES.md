# DeepEye 后端改动说明

## Event Sourcing 架构

### 核心思想

**事件是唯一的真相来源 (Single Source of Truth)**

- 所有 Agent 执行事件既推送到 Redis（实时）也持久化到 PostgreSQL（历史）
- 前端使用**同一套 `processEvent()` 函数**处理实时和历史数据
- 无需在工具返回值中嵌入子步骤，架构更清晰

### 架构图

```
┌───────────────────────────────────────────────────────────────────────────┐
│                                Frontend (Vue 3)                           │
│                                                                           │
│     ┌─────────────────────────────────────────────────────────────┐       │
│     │  processEvent()  ◄───── SSE Events (real-time)              │       │
│     │        │         ◄───── /api/sessions/{id}/history (replay) │       │
│     └────────┼────────────────────────────────────────────────────┘       │
│              │ Same event processing logic                                │
└──────────────┼────────────────────────────────────────────────────────────┘
               ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                             Backend                                       │
│                                                                           │
│   ┌─────────────┐         ┌─────────────────────────────────────────┐    │
│   │ FastAPI API │         │          Celery Worker                  │    │
│   │             │         │   ┌──────────────────────────────────┐  │    │
│   │ POST /chat  │────────►│   │ EventSourcedCallback             │  │    │
│   │             │         │   │   ├─ _emit() → Redis (real-time) │  │    │
│   │             │         │   │   └─ _persist() → PostgreSQL     │  │    │
│   └─────────────┘         │   └──────────────────────────────────┘  │    │
│                           │                                          │    │
│                           │   SupervisorAgent → SQLAgent/CodeAgent   │    │
│                           └──────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                           Storage Layer                                   │
│                                                                           │
│   ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐      │
│   │   PostgreSQL    │    │      Redis      │    │  LangGraph      │      │
│   │   agent_events  │    │   (Pub/Sub)     │    │  Checkpoint     │      │
│   │   (历史持久化)   │    │   (实时推送)    │    │  (Agent State)  │      │
│   └─────────────────┘    └─────────────────┘    └─────────────────┘      │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## 关键改动

### 1. Event Sourcing 实现

#### 新增 `AgentEventRecord` 模型 (`models/agent_event.py`)

```python
class AgentEventRecord(Base):
    __tablename__ = "agent_events"

    id: int (primary key)
    session_id: str     # 关联会话
    sequence: int       # 事件序号，用于重放顺序
    event_type: str     # token, tool_start, tool_end, etc.
    source: str         # supervisor, sql_agent, code_agent
    content: str | None # token 内容或错误信息
    data: JSON | None   # 工具调用的结构化数据
    created_at: datetime
```

#### 重写 `EventSourcedCallback` (`callbacks.py`)

```python
class EventSourcedCallback(BaseCallbackHandler):
    """事件既推送到 Redis 也持久化到数据库"""

    async def _emit(self, event: AgentEvent) -> None:
        # 1. 推送到 Redis (实时)
        await self.redis_client.publish(self.channel, event.model_dump_json())
        # 2. 持久化到 PostgreSQL (历史)
        self._persist_event(event)
```

#### 更新历史 API (`sessions.py`)

```python
@router.get("/{session_id}/history")
def get_session_history(session_id: str, db: Session = Depends(get_db)):
    """返回事件列表，前端重放这些事件来重建 UI"""
    events = db.query(AgentEventRecord)\
        .filter_by(session_id=session_id)\
        .order_by(asc(sequence)).all()
    return {"events": [e.to_dict() for e in events]}
```

### 2. 用户消息持久化 (`chat.py`)

```python
@router.post("/chat")
async def start_chat(request: ChatRequest, db: Session = Depends(get_db)):
    # ...
    # 持久化用户消息为事件
    _persist_user_message(db, session_id, request.message)
    # ...
```

---

## 事件类型

| 事件类型 | 说明 | 来源 |
|----------|------|------|
| `user_message` | 用户输入 | API |
| `agent_start` | Agent 开始执行 | Supervisor |
| `agent_end` | Agent 执行完成 | Supervisor |
| `token` | 流式输出 token | Supervisor/SubAgent |
| `tool_start` | 工具调用开始 | Supervisor/SubAgent |
| `tool_end` | 工具调用完成 | Supervisor/SubAgent |
| `error` | 错误信息 | Any |

---

## 数据流

```
实时流:
  User → POST /chat → Celery Task → EventSourcedCallback
                                          │
                                          ├─→ Redis Pub/Sub → SSE → Frontend
                                          │
                                          └─→ PostgreSQL (agent_events)

历史重放:
  Frontend → GET /sessions/{id}/history → PostgreSQL → events[]
                                                           │
                                                           ▼
                                               Frontend processEvent() loop
```

---

## 配置项

| 变量 | 用途 |
|------|------|
| `REDIS_URL` | Celery Broker + Pub/Sub |
| `SQLALCHEMY_DATABASE_URL` | 业务数据库 (sessions, datasources, agent_events) |
| `POSTGRES_STATE_URL` | LangGraph Checkpoint 存储 |

