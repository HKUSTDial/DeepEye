"""Agent workflow Celery tasks."""

import asyncio
import traceback
import uuid

from langchain_openai import ChatOpenAI
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from sqlalchemy import MetaData, Table, create_engine, inspect, select

from app.core.celery_app import celery_app
from app.core.config import settings
from app.infra import RedisEventBus
from app.repositories import DataSourceRepository, SessionAttachmentRepository, SessionRepository
from app.sandbox import sandbox_manager
from app.sandbox.manager import _get_datasource_filename
from app.schemas import AgentEvent, AgentEventType, AgentInput, UserMessage, SandboxEvent, SandboxEventType
from app.services.workflow_engine import build_registry
from app.services.agent_prompts import build_supervisor_prompt
from app.services.workflow_prompts import build_workflow_prompt
from app.services.workflow_tracking_service import (
    complete_chat_turn_record,
    create_chat_turn_record,
    fail_chat_turn_record,
)
from app.tasks.callbacks import AgentCallback, MessageCollector, persist_message
from app.tasks.db import task_session_scope
from deepeye.agents import AgentFactory
from app.tools.workflow_tools import (
    create_design_workflow_tool,
    create_summarize_workflow_result_tool,
)
from deepeye.utils.logger import logger

_SCHEMA_PREVIEW_ROWS = 3


def _build_failure_message(error: Exception) -> str:
    message = str(error)
    if "GraphRecursionError" in message or "Recursion limit" in message:
        return "工作流规划未收敛，系统已停止自动重试。"
    return "工作流规划或执行失败。"


def _get_datasources_info(datasource_ids: list[str] | None, user_id: uuid.UUID | None = None) -> list[dict[str, str]]:
    if not datasource_ids:
        return []
    items = []
    with task_session_scope() as db:
        for ds_id in datasource_ids:
            try:
                ds_uuid = uuid.UUID(ds_id)
            except (ValueError, TypeError):
                continue
            ds = DataSourceRepository(db).get_by_id_and_user(ds_uuid, user_id) if user_id else DataSourceRepository(db).get(ds_uuid)
            if ds:
                info = {
                    "id": str(ds.id),
                    "name": ds.name,
                    "type": ds.type,
                    "category": getattr(ds, "category", "database"),
                }
                if info["category"] == "file":
                    original_filename = _get_datasource_filename(ds)
                    info["local_path"] = f"/workspace/data/{original_filename}"
                items.append(info)
    return items


def _get_database_table_preview(data_engine, table_name: str, limit: int = _SCHEMA_PREVIEW_ROWS) -> list[dict[str, object]]:
    try:
        metadata = MetaData()
        table = Table(table_name, metadata, autoload_with=data_engine)
        with data_engine.connect() as conn:
            rows = conn.execute(select(table).limit(limit)).mappings().all()
        return [dict(row) for row in rows]
    except Exception as exc:
        logger.warning("Failed to fetch preview rows for table %s: %s", table_name, exc)
        return []


def _get_datasources_schema(
    datasource_ids: list[str] | None,
    user_id: uuid.UUID | None = None,
    max_tables: int = 20,
    max_columns: int = 20,
    preview_rows: int = _SCHEMA_PREVIEW_ROWS,
) -> list[dict[str, object]]:
    if not datasource_ids:
        return []
    all_schemas = []
    
    with task_session_scope() as db:
        for ds_id in datasource_ids:
            try:
                ds_uuid = uuid.UUID(ds_id)
            except (ValueError, TypeError):
                continue
            ds = DataSourceRepository(db).get_by_id_and_user(ds_uuid, user_id) if user_id else DataSourceRepository(db).get(ds_uuid)
            if not ds:
                continue
            
            category = getattr(ds, "category", "database")
            if category == "database":
                connection_string = ds.connection_string
                if not connection_string:
                    continue
                try:
                    from app.node.core.db_utils import normalize_connection_string
                    from app.node.core.db_utils import json_safe_row

                    data_engine = create_engine(normalize_connection_string(connection_string))
                    inspector = inspect(data_engine)
                    tables = inspector.get_table_names()[:max_tables]
                    
                    for name in tables:
                        columns = inspector.get_columns(name)[:max_columns]
                        preview = _get_database_table_preview(data_engine, name, limit=preview_rows)
                        all_schemas.append({
                            "datasource_id": str(ds.id),
                            "datasource_name": ds.name,
                            "name": name,
                            "kind": "table",
                            "columns": [{"name": col.get("name"), "type": str(col.get("type"))} for col in columns],
                            "preview": [json_safe_row(dict(row)) for row in preview],
                        })
                except Exception as e:
                    logger.warning(f"Failed to get schema for DB {ds.name}: {e}")
            elif category == "file":
                metadata = getattr(ds, "file_metadata", {})
                if metadata and "columns" in metadata:
                    all_schemas.append({
                        "datasource_id": str(ds.id),
                        "datasource_name": ds.name,
                        "name": ds.name,
                        "kind": "file",
                        "local_path": f"/workspace/data/{_get_datasource_filename(ds)}",
                        "columns": metadata["columns"],
                        "preview": (metadata.get("preview", []) or [])[:preview_rows],
                    })
    return all_schemas


def _create_model() -> ChatOpenAI:
    return ChatOpenAI(
        api_key=settings.LLM_API_KEY,
        base_url=settings.LLM_BASE_URL,
        model=settings.LLM_MODEL,
        temperature=settings.LLM_TEMPERATURE,
        streaming=True,
    )


def _get_user_id(session_id: str) -> uuid.UUID | None:
    try:
        session_uuid = uuid.UUID(session_id)
    except (TypeError, ValueError):
        return None
    with task_session_scope() as db:
        session = SessionRepository(db).get(session_uuid)
        return session.user_id if session else None


def _get_session_attachment_ids(session_id: str) -> list[str]:
    try:
        session_uuid = uuid.UUID(session_id)
    except (TypeError, ValueError):
        return []
    with task_session_scope() as db:
        return SessionAttachmentRepository(db).list_datasource_ids(session_uuid)


async def _run_agent_async(agent_input: AgentInput) -> None:
    session_id = agent_input.session_id
    model = _create_model()
    event_bus = RedisEventBus(settings.REDIS_URL)
    user_id = _get_user_id(session_id)

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
        else _get_session_attachment_ids(session_id)
    )
    
    # Sync file datasources
    file_datasources = []
    with task_session_scope() as db:
        for ds_id in datasource_ids:
            try:
                ds_uuid = uuid.UUID(ds_id)
            except (TypeError, ValueError):
                continue
            ds = (
                DataSourceRepository(db).get_by_id_and_user(ds_uuid, user_id)
                if user_id
                else DataSourceRepository(db).get(ds_uuid)
            )
            if ds and getattr(ds, "category", "database") == "file":
                file_datasources.append(ds)
    
    if file_datasources:
        logger.info(f"[AgentTask] Syncing {len(file_datasources)} file datasources to sandbox")
        await sandbox_manager.sync_datasource_files(session_id, file_datasources)

    # Build tools - all agents share the same sandbox
    logger.info("[AgentTask] Building tools...")
    tools = []
    datasources_info = _get_datasources_info(datasource_ids, user_id)
    datasources_schema = _get_datasources_schema(datasource_ids, user_id)
    
    # Prepare datasource context for Supervisor. Include id/path so workflow
    # node params (e.g. datasource ids and schema-aware workflow params) can be filled precisely.
    ds_context_lines = []
    for ds in datasources_info:
        line = f"- id: {ds['id']}, name: {ds['name']} ({ds['category']})"
        if ds['category'] == 'file':
            line += f", path: {ds.get('local_path', '')}"
        ds_context_lines.append(line)
    header = "Available Data Sources (use the file paths for workflow nodes like report.generate):\n"
    datasources_context = header + "\n".join(ds_context_lines) if ds_context_lines else "No data sources selected."

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
