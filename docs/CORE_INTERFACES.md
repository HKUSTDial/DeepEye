# DeepEye 核心接口文档

本文档描述 DeepEye 的三个核心抽象接口，它们是系统扩展性和可测试性的基础。

---

## 1. BaseAgent (`packages/core`)

**位置**: `deepeye/agents/base.py`

Agent 的抽象基类，定义所有 Agent 必须实现的接口。

### 接口定义

```python
from abc import ABC, abstractmethod
from typing import List, Any, AsyncIterator
from langchain_core.language_models import BaseChatModel
from langgraph.checkpoint.base import BaseCheckpointSaver

class BaseAgent(ABC):
    """Abstract base class for all DeepEye agents."""

    def __init__(
        self,
        model: BaseChatModel,
        tools: List[Any] | None = None,
        system_prompt: str = "",
        checkpointer: BaseCheckpointSaver | None = None,
    ):
        self.model = model
        self.tools = tools or []
        self.system_prompt = system_prompt
        self.checkpointer = checkpointer
        self.graph = self._build_graph()

    @abstractmethod
    def _build_graph(self) -> Any:
        """Build and return the compiled LangGraph workflow."""

    @abstractmethod
    async def ainvoke(
        self, input_message: str, thread_id: str | None = None, config: dict | None = None
    ) -> dict:
        """Run the agent with a single input message."""

    @abstractmethod
    async def astream(
        self, input_message: str, thread_id: str | None = None, config: dict | None = None
    ) -> AsyncIterator[Any]:
        """Async generator to stream events from the agent."""
```

### 现有实现

- **ReActAgent**: ReAct 风格的工具调用 Agent
- **SupervisorAgent**: 带规划能力的协调者 Agent
- **SQLAgent**: 专门用于数据库查询
- **CodeAgent**: 专门用于 Python 代码执行

### 扩展示例

```python
class MyCustomAgent(BaseAgent):
    def _build_graph(self):
        workflow = StateGraph(AgentState)
        workflow.add_node("process", self._process)
        workflow.set_entry_point("process")
        workflow.add_edge("process", END)
        return workflow.compile(checkpointer=self.checkpointer)

    async def ainvoke(self, input_message, thread_id=None, config=None):
        return await self.graph.ainvoke({"messages": [HumanMessage(content=input_message)]}, config=config)

    async def astream(self, input_message, thread_id=None, config=None):
        async for event in self.graph.astream_events(...):
            yield event
```

---

## 2. BaseRepository (`packages/backend`)

**位置**: `app/repositories/base.py`

数据访问的抽象接口，遵循 Repository 模式。

### 接口定义

```python
from abc import ABC, abstractmethod
from typing import Generic, TypeVar
from uuid import UUID

T = TypeVar("T")
ID = TypeVar("ID", str, UUID, int)

class BaseRepository(ABC, Generic[T, ID]):
    """Abstract repository for aggregate persistence."""

    @abstractmethod
    def get(self, id: ID) -> T | None: ...

    @abstractmethod
    def save(self, entity: T) -> T: ...

    @abstractmethod
    def delete(self, id: ID) -> None: ...

    @abstractmethod
    def find_all(self, skip: int = 0, limit: int = 100) -> list[T]: ...
```

### SQLAlchemy 实现

```python
class SQLAlchemyRepository(BaseRepository[ModelT, ID]):
    def __init__(self, db: Session, model_class: type[ModelT]):
        self.db = db
        self.model_class = model_class

    def get(self, id: ID) -> ModelT | None: ...
    def save(self, entity: ModelT) -> ModelT: ...
    def delete(self, id: ID) -> None: ...
    def find_all(self, skip: int = 0, limit: int = 100) -> list[ModelT]: ...
    def find_all_desc(self, order_by: str, skip: int = 0, limit: int = 100) -> list[ModelT]: ...
```

### 现有实现

- **SessionRepository**: ChatSession 数据访问
- **EventRepository**: AgentEvent 事件存储/读取
- **DataSourceRepository**: DataSource 管理

### 扩展示例

```python
class UserRepository(SQLAlchemyRepository[User, UUID]):
    def __init__(self, db: Session):
        super().__init__(db, User)

    def find_by_email(self, email: str) -> User | None:
        return self.db.query(User).filter(User.email == email).first()
```

---

## 3. EventBus (`packages/backend`)

**位置**: `app/infra/event_bus.py`

事件发布的抽象接口，解耦事件生产者和传输实现。使用**同步**接口以避免 Celery 事件循环冲突。

### 接口定义

```python
from abc import ABC, abstractmethod

class EventBus(ABC):
    """Abstract event bus for publishing events."""

    @abstractmethod
    def publish(self, channel: str, data: str) -> None: ...

    @abstractmethod
    def close(self) -> None: ...
```

### Redis 实现

```python
class RedisEventBus(EventBus):
    """Redis Pub/Sub implementation using sync client."""

    def __init__(self, redis_url: str):
        self.redis_url = redis_url
        self._client: redis.Redis | None = None

    @property
    def client(self) -> redis.Redis:
        if self._client is None:
            self._client = redis.from_url(self.redis_url)
        return self._client

    def publish(self, channel: str, data: str) -> None:
        self.client.publish(channel, data)

    def close(self) -> None:
        if self._client:
            self._client.close()
            self._client = None
```

### 扩展示例

```python
class KafkaEventBus(EventBus):
    def __init__(self, bootstrap_servers: str):
        self.producer = KafkaProducer(bootstrap_servers=bootstrap_servers)

    def publish(self, channel: str, data: str) -> None:
        self.producer.send(channel, data.encode())

    def close(self) -> None:
        self.producer.close()


class InMemoryEventBus(EventBus):
    """用于测试的内存实现。"""
    def __init__(self):
        self.messages: list[tuple[str, str]] = []

    def publish(self, channel: str, data: str) -> None:
        self.messages.append((channel, data))

    def close(self) -> None:
        pass
```

---

## 设计原则

| 原则 | 说明 |
|------|------|
| **依赖倒置** | 上层依赖抽象接口，不直接依赖具体实现 |
| **接口隔离** | 每个接口只定义单一职责的方法 |
| **开闭原则** | 扩展新实现无需修改现有代码 |

## 测试策略

- **Repository**: 使用 SQLite in-memory 或 mock
- **EventBus**: 使用 `InMemoryEventBus`
- **Agent**: mock `model` 和 `tools`

