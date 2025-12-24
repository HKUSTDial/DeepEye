# DeepEye 架构重构文档

## 概述

本次重构对 `packages/backend` 和 `packages/core` 进行了全面优化，目标是：
- **简洁性**：移除冗余代码和过度抽象
- **扩展性**：引入必要的分层架构
- **一致性**：统一代码风格和设计模式

---

## 代码变更统计

```
19 files changed, 437 insertions(+), 864 deletions(-)
```

**净减少 427 行代码**，同时提升了架构质量。

---

## 一、Backend 改动 (`packages/backend`)

### 1.1 新增模块

| 目录 | 职责 |
|------|------|
| `app/repositories/` | 数据访问层（`BaseRepository`, `SQLAlchemyRepository`, `SessionRepository`, `EventRepository`, `DataSourceRepository`） |
| `app/services/` | 业务逻辑（`get_or_create_session`, `start_agent_workflow`） |
| `app/schemas/` | 拆分后的 Pydantic 模型（`api.py`, `events.py`, `internal.py`） |
| `app/infra/` | 基础设施抽象（`EventBus`, `RedisEventBus`） |
| `app/api/sessions.py` | Session CRUD 端点（从 `chat.py` 拆分） |

### 1.2 删除的文件

| 文件 | 原因 |
|------|------|
| `app/api/schemas.py` | 拆分为 `app/schemas/` 下的多个文件 |

### 1.3 重构的文件

#### `app/api/chat.py`
- **之前**：202 行，包含 session 管理、SSE 流、所有 schemas
- **之后**：~70 行，只负责 `/chat` 和 `/stream` 端点
- **改进**：使用 `get_or_create_session()` 函数和 `EventRepository`

#### `app/api/datasource.py`
- **之前**：直接操作 `db.query(DataSource)`
- **之后**：使用 `DataSourceRepository`
- **改进**：风格统一，添加 `prefix="/datasources"`

#### `app/tasks/agent_tasks.py`
- **之前**：198 行，硬编码 Agent 创建、散落的 Redis 客户端
- **之后**：~98 行
- **改进**：
  - 使用 `AgentFactory` 创建 Agent
  - 使用 `RedisEventBus` 抽象事件发布
  - 使用 `DataSourceRepository` 获取数据源

#### `app/tasks/callbacks.py`
- **之前**：`EventSourcedCallback` 直接依赖 `redis.asyncio.Redis`
- **之后**：`AgentCallback` 依赖抽象 `EventBus`
- **改进**：可替换为 Kafka、内存实现等

#### `app/db/session.py`
- 移除多余注释，保持 SQLAlchemy 标准写法

---

## 二、Core 改动 (`packages/core`)

### 2.1 新增模块

| 文件 | 职责 |
|------|------|
| `agents/__init__.py` | 统一导出所有 Agent |
| `agents/factory.py` | `AgentFactory` - 统一创建 Agent |
| `agents/react_agent.py` | 从 `base.py` 拆分的 ReAct 实现 |
| `tools/__init__.py` | 统一导出所有工具 |
| `graph/__init__.py` | 统一导出 |

### 2.2 重构的文件

#### `agents/base.py`
- **之前**：124 行，混合了抽象基类和 ReAct 实现
- **之后**：45 行，纯抽象基类
- **改进**：职责单一，只定义接口

#### `agents/supervisor.py`
- **之前**：直接构造 workflow
- **之后**：继承 `ReActAgent`，只覆写 `_call_model` 注入动态 plan
- **改进**：复用 ReAct 逻辑

#### `tools/agent_tools.py`
- 简化子 Agent 工具创建逻辑

#### `graph/state.py`
- 简化 reducer 函数

---

## 三、架构设计决策

### 3.1 引入 Repository 模式

```
API Layer → Repository → Database
```

**为什么**：
- 统一数据访问接口
- 便于测试（可 mock Repository）
- 避免 API 层直接写 SQL

**实现**：
```python
class SQLAlchemyRepository(BaseRepository[ModelT, ID]):
    def get(self, id: ID) -> ModelT | None: ...
    def save(self, entity: ModelT) -> ModelT: ...
    def delete(self, id: ID) -> None: ...
    def find_all(self, skip: int, limit: int) -> list[ModelT]: ...
    def find_all_desc(self, order_by: str, skip: int, limit: int) -> list[ModelT]: ...
```

### 3.2 引入 EventBus 抽象

```python
class EventBus(ABC):
    async def publish(self, channel: str, data: str) -> None: ...
    async def close(self) -> None: ...
```

**为什么**：
- 解耦事件发布和具体实现
- 当前用 Redis，未来可换 Kafka
- 便于本地测试（内存实现）
- 使用**异步**接口，所有调用点都在 async 上下文中

### 3.3 引入 AgentFactory

```python
class AgentFactory:
    def create_supervisor(self, tools: list) -> SupervisorAgent: ...
```

**为什么**：
- 统一 Agent 创建逻辑
- 避免在 task 中硬编码
- 未来可扩展 `create_sql_agent()`, `create_code_agent()`

### 3.4 移除过度抽象

| 移除 | 原因 |
|------|------|
| `BaseEvent`, `BaseEntity`, `BaseData` | 未被有效使用 |
| `EventStore` 抽象 | `EventRepository` 足够 |
| ORM Mixins | 增加复杂度，收益低 |
| `SessionService` 类 | 改为函数 `get_or_create_session()` |
| `ChatService` 类 | 改为函数 `start_agent_workflow()` |

---

## 四、扩展性提升

### 4.1 新增 Agent 类型

```python
# agents/factory.py
def create_research_agent(self, tools: list) -> ResearchAgent:
    return ResearchAgent(model=self.model, tools=tools, checkpointer=self.checkpointer)
```

### 4.2 新增数据实体

```python
# repositories/xxx_repo.py
class XxxRepository(SQLAlchemyRepository[XxxModel, uuid.UUID]):
    def __init__(self, db: Session):
        super().__init__(db, XxxModel)
```

### 4.3 更换事件总线

```python
# infra/kafka_event_bus.py
class KafkaEventBus(EventBus):
    async def publish(self, channel: str, data: str) -> None:
        await self.producer.send(channel, data.encode())

    async def close(self) -> None:
        await self.producer.stop()
```

---

## 五、目录结构对比

### 之前
```
packages/backend/app/
├── api/
│   ├── chat.py (含 session CRUD + SSE + schemas)
│   ├── datasource.py
│   └── schemas.py
├── models/
├── tasks/
└── ...
```

### 之后
```
packages/backend/app/
├── api/           # HTTP 端点
│   ├── chat.py          # /chat, /chat/{id}/stream
│   ├── sessions.py      # /sessions CRUD
│   └── datasource.py    # /datasources CRUD
├── core/          # 配置
│   ├── config.py
│   └── celery_app.py
├── db/            # 数据库
│   └── session.py
├── infra/         # 基础设施抽象
│   └── event_bus.py     # EventBus, RedisEventBus
├── models/        # ORM 模型
│   ├── agent_event.py
│   ├── chat_session.py
│   └── datasource.py
├── repositories/  # 数据访问层
│   ├── base.py          # BaseRepository, SQLAlchemyRepository
│   ├── session_repo.py
│   ├── event_repo.py
│   └── datasource_repo.py
├── schemas/       # Pydantic 模型
│   ├── api.py           # Request/Response schemas
│   ├── events.py        # AgentEvent, AgentEventType
│   └── internal.py      # AgentInput (内部传递)
├── services/      # 业务函数
│   ├── chat_service.py      # start_agent_workflow
│   └── session_service.py   # get_or_create_session
├── tasks/         # Celery 任务
│   ├── agent_tasks.py   # run_agent_workflow
│   └── callbacks.py     # AgentCallback
├── main.py
└── worker.py
```

---

## 六、总结

| 指标 | 之前 | 之后 |
|------|------|------|
| 代码行数 | 多 | 减少 427 行 |
| 抽象层级 | 过度或缺失 | 恰当 |
| 职责划分 | 混乱 | 清晰分层 |
| 扩展新 Agent | 改 task 代码 | 用 Factory |
| 换事件总线 | 改多处 | 实现 EventBus |
| 测试友好度 | 难 mock | Repository/EventBus 可 mock |

---

## 七、后续优化 (2024-12)

### 7.1 修复 Celery Fork 安全问题

**问题**：模块级 SQLAlchemy Engine 在 Celery prefork 模式下会导致连接共享问题。

| 文件 | 修改前 | 修改后 |
|------|--------|--------|
| `tasks/callbacks.py` | 模块级 `_engine`, `_SessionLocal` | `_get_session()` 函数，每次调用创建新连接 |
| `tasks/agent_tasks.py` | 模块级 `_engine`, `_Session` | 在函数内部创建，用完即弃 |

**原因**：Celery prefork worker 在 fork 后复制父进程内存，模块级 Engine 的连接池会被多进程共享，导致：
- "SSL SYSCALL error"
- 连接池状态不一致

### 7.2 核心接口说明

详细接口说明见 [`CORE_INTERFACES.md`](./CORE_INTERFACES.md)。
