"""Agent workflow Celery tasks."""

import asyncio
import traceback

from langchain_openai import ChatOpenAI
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from app.core.celery_app import celery_app
from app.core.config import settings
from app.infra import RedisEventBus
from app.sandbox import sandbox_manager
from app.schemas import AgentEvent, AgentEventType, AgentInput, UserMessage, SandboxEvent, SandboxEventType
from app.workflow.services.engine import build_registry
from app.agent.prompts import build_supervisor_prompt
from app.workflow.prompts import build_workflow_prompt
from app.workflow.services.tracking import (
    complete_chat_turn_record,
    create_chat_turn_record,
    fail_chat_turn_record,
)
from app.tasks.callbacks import AgentCallback, MessageCollector, persist_message
from app.tasks.agent_datasources import (
    build_datasources_context,
    get_datasources_info,
    get_datasources_schema,
    get_session_attachment_ids,
    get_user_id,
    list_file_datasources,
)
from deepeye.agents import AgentFactory
from app.tools.workflow_tools import (
    create_design_workflow_tool,
    create_summarize_workflow_result_tool,
)
from deepeye.utils.logger import logger


def _build_failure_message(error: Exception) -> str:
    message = str(error)
    if "GraphRecursionError" in message or "Recursion limit" in message:
        return "工作流规划未收敛，系统已停止自动重试。"
    return "工作流规划或执行失败。"


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
    user_id = get_user_id(session_id)

    # Persist user message first
    user_message = persist_message(session_id, UserMessage(content=agent_input.user_input))
    turn = create_chat_turn_record(
        session_id,
        user_id,
        agent_input.user_input,
        user_message_id=user_message.id if user_message else None,
    )
    turn_id = str(turn.id) if turn else None

    # Shared collector for all callbacks
    collector = MessageCollector()

    # Callbacks for different sources - all share the same collector
    user_id_str = str(user_id) if user_id else None
    cb_supervisor = AgentCallback(
        event_bus,
        session_id,
        "supervisor",
        user_id=user_id_str,
        turn_id=turn_id,
        collector=collector,
        ignore_tags=["sub_agent"],
    )
    cb_workflow = AgentCallback(
        event_bus,
        session_id,
        "workflow_agent",
        user_id=user_id_str,
        turn_id=turn_id,
        collector=collector,
    )
    # Get existing sandbox or create new one (reuse within session)
    channel = f"session:{session_id}"
    logger.info(f"[AgentTask] Getting or creating sandbox for session: {session_id}")
    await sandbox_manager.get_or_create_sandbox(session_id)
    
    # Notify frontend that sandbox is ready (to open files panel)
    logger.info("[AgentTask] Sandbox ready, publishing STARTED event")
    await event_bus.publish(
        channel, 
        SandboxEvent(type=SandboxEventType.STARTED, source="sandbox").model_dump_json()
    )
    
    # Build tool - handle data sources
    datasource_ids = (
        list(dict.fromkeys(agent_input.datasource_ids))
        if agent_input.datasource_ids is not None
        else get_session_attachment_ids(session_id)
    )
    
    # Sync file datasources
    file_datasources = list_file_datasources(datasource_ids, user_id)
    
    if file_datasources:
        logger.info(f"[AgentTask] Syncing {len(file_datasources)} file datasources to sandbox")
        await sandbox_manager.sync_datasource_files(session_id, file_datasources)

    # Build tools - all agents share the same sandbox
    logger.info("[AgentTask] Building tools...")
    tools = []
    datasources_info = get_datasources_info(datasource_ids, user_id)
    datasources_schema = get_datasources_schema(datasource_ids, user_id)
    datasources_context = build_datasources_context(datasources_info)

    workflow_prompt = build_workflow_prompt(
        build_registry(),
        datasource=datasources_info,  # Now a list
        tables=datasources_schema,    # Now includes datasource_id/name
    )
    tools.append(
        create_design_workflow_tool(
            model,
            session_id,
            workflow_prompt,
            callbacks=[cb_workflow],
            turn_id=turn_id,
        )
    )
    tools.append(
        create_summarize_workflow_result_tool(
            model,
            session_id,
            turn_id=turn_id,
        )
    )

    user_input = agent_input.user_input

    logger.info("[AgentTask] Setting up LangGraph checkpointer...")
    async with AsyncPostgresSaver.from_conn_string(settings.POSTGRES_STATE_URL) as checkpointer:
        await checkpointer.setup()

        logger.info("[AgentTask] Creating supervisor agent...")
        factory = AgentFactory(model, checkpointer)
        supervisor = factory.create_supervisor(
            tools,
            system_prompt_template=build_supervisor_prompt(),
        )

        try:
            logger.info("[AgentTask] Starting agent execution...")
            await cb_supervisor._publish(AgentEvent(type=AgentEventType.AGENT_START))
            await supervisor.ainvoke(
                user_input,
                thread_id=session_id,
                config={
                    "callbacks": [cb_supervisor],
                    "configurable": {
                        "datasources_context": datasources_context
                    }
                },
            )
            logger.info("[AgentTask] Agent execution finished successfully")
            # Build and persist the complete assistant message
            assistant_message = collector.build()
            assistant_record = persist_message(session_id, assistant_message)
            complete_chat_turn_record(
                turn_id,
                assistant_message_id=assistant_record.id if assistant_record else None,
            )
            await cb_supervisor._publish(AgentEvent(type=AgentEventType.AGENT_END))
        except Exception as e:
            tb = traceback.format_exc()
            logger.error(f"[AgentTask] Error: {tb}")
            assistant_record = None
            if collector.has_activity():
                partial_message = collector.build(fallback_content=_build_failure_message(e))
                assistant_record = persist_message(session_id, partial_message)
            fail_chat_turn_record(
                turn_id,
                str(e),
                assistant_message_id=assistant_record.id if assistant_record else None,
            )
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
