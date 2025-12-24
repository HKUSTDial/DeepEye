"""Agent workflow Celery tasks."""

import asyncio
import traceback

from langchain_openai import ChatOpenAI
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.celery_app import celery_app
from app.core.config import settings
from app.infra import RedisEventBus
from app.repositories import DataSourceRepository
from app.schemas import AgentEvent, AgentEventType, AgentInput, UserMessage
from app.tasks.callbacks import AgentCallback, MessageCollector, persist_message
from deepeye.agents import AgentFactory
from deepeye.tools.agent_tools import create_code_agent_tool, create_sql_agent_tool


def _get_datasource_url(datasource_id: str | None) -> str | None:
    """Fetch datasource connection string, creating fresh DB session per-call."""
    if not datasource_id:
        return None
    engine = create_engine(settings.SQLALCHEMY_DATABASE_URL)
    Session = sessionmaker(bind=engine)
    with Session() as db:
        ds = DataSourceRepository(db).get(datasource_id)
        return ds.connection_string if ds else None


def _create_model() -> ChatOpenAI:
    return ChatOpenAI(
        api_key=settings.LLM_API_KEY,
        base_url=settings.LLM_BASE_URL,
        model=settings.LLM_MODEL,
        temperature=settings.LLM_TEMPERATURE,
        streaming=True,
    )


async def _run_agent_async(agent_input: AgentInput) -> None:
    session_id = agent_input.session_id
    model = _create_model()
    event_bus = RedisEventBus(settings.REDIS_URL)

    # Persist user message first
    persist_message(session_id, UserMessage(content=agent_input.user_input))

    # Shared collector for all callbacks
    collector = MessageCollector()

    # Callbacks for different sources - all share the same collector
    cb_supervisor = AgentCallback(event_bus, session_id, "supervisor", collector, ignore_tags=["sub_agent"])
    cb_sql = AgentCallback(event_bus, session_id, "sql_agent", collector)
    cb_code = AgentCallback(event_bus, session_id, "code_agent", collector)

    # Build tools based on available datasource
    tools = []
    db_url = _get_datasource_url(agent_input.datasource_id)
    if db_url:
        tools.append(create_sql_agent_tool(db_url, model, callbacks=[cb_sql]))
    tools.append(create_code_agent_tool(settings.SANDBOX_URL, model, callbacks=[cb_code]))

    async with AsyncPostgresSaver.from_conn_string(settings.POSTGRES_STATE_URL) as checkpointer:
        await checkpointer.setup()

        factory = AgentFactory(model, checkpointer)
        supervisor = factory.create_supervisor(tools)

        try:
            await cb_supervisor._publish(AgentEvent(type=AgentEventType.AGENT_START))
            await supervisor.ainvoke(
                agent_input.user_input,
                thread_id=session_id,
                config={"callbacks": [cb_supervisor]},
            )
            # Build and persist the complete assistant message
            assistant_message = collector.build()
            persist_message(session_id, assistant_message)
            await cb_supervisor._publish(AgentEvent(type=AgentEventType.AGENT_END))
        except Exception as e:
            tb = traceback.format_exc()
            print(f"Agent Error: {tb}")
            await cb_supervisor._publish(AgentEvent(type=AgentEventType.ERROR, content=str(e), data={"traceback": tb}))
        finally:
            await event_bus.close()


@celery_app.task(bind=True)
def run_agent_workflow(self, agent_input_dict: dict) -> dict:
    """Celery task: execute Supervisor Agent workflow."""
    try:
        agent_input = AgentInput(**agent_input_dict)
    except Exception as e:
        return {"status": "error", "error": str(e)}

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(_run_agent_async(agent_input))
    finally:
        loop.close()

    return {"status": "finished", "session_id": agent_input.session_id}
