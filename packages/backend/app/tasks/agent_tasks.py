import asyncio
import json
import redis.asyncio as redis
from celery import shared_task
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from psycopg_pool import AsyncConnectionPool
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from deepeye.agents.supervisor import SupervisorAgent
from deepeye.tools.agent_tools import create_sql_agent_tool, create_code_agent_tool
from deepeye.utils.logger import AgentStreamLogger
from app.core.config import settings
from app.api.schemas import AgentEvent, AgentInput, AgentEventType
from langchain_core.messages import BaseMessage
from app.models.datasource import DataSource
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import traceback

from app.tasks.callbacks import RedisStreamingCallback


def get_connection_string(datasource_id: str | None) -> str | None:
    """
    Retrieve connection string from DB by ID.
    """
    # Fallback to env var if no ID provided
    if not datasource_id:
        return None
        
    # We need to create a new synchronous session here because Celery tasks can be sync/async
    # But since _run_agent_async is async, we could use async sqlalchemy, 
    # but for simplicity let's use the sync engine we already defined in app.db.session
    # Note: app.db.session.SessionLocal is a sessionmaker
    
    # However, we are inside a different process (worker), so we need to ensure the engine is created correctly.
    # The 'app.db.session' module should handle engine creation.
    
    # Create a fresh engine/session to be safe in multiprocessing context
    # Or just reuse the one from app.db.session if it's safe. 
    # Usually engine is thread-safe but connection sharing across fork() can be tricky.
    # For now, let's create a temporary engine to be absolutely safe and avoid "SSL error: decryption failed or bad record mac"
    
    engine = create_engine(settings.SQLALCHEMY_DATABASE_URL)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        # We need to cast the string ID to UUID for postgres query
        ds = session.query(DataSource).filter(DataSource.id == datasource_id).first()
        if ds:
            return ds.connection_string
        return None
    except Exception as e:
        print(f"Error fetching datasource: {e}")
        return None
    finally:
        session.close()
        engine.dispose()

async def _run_agent_async(agent_input: AgentInput):
    """
    Async implementation of the agent workflow.
    """
    session_id = agent_input.session_id
    user_input = agent_input.user_input
    datasource_id = agent_input.datasource_id
    
    # 1. Initialize Tools & Agent (Similar to full_pipeline.py)
    model = ChatOpenAI(
        api_key=settings.LLM_API_KEY,
        base_url=settings.LLM_BASE_URL,
        model=settings.LLM_MODEL,
        temperature=settings.LLM_TEMPERATURE,
        streaming=True,
    )
    
    # 3. Connect to Redis for Pub/Sub
    redis_client = redis.from_url(settings.REDIS_URL)
    channel = f"session:{session_id}"
    
    # --- Callbacks Initialization ---
    # 1. Callback for Sub-Agents (e.g. SQL Agent)
    sql_agent_callback = RedisStreamingCallback(redis_client, channel, source="sql_agent")
    # 2. Callback for Code Agent
    code_agent_callback = RedisStreamingCallback(redis_client, channel, source="code_agent")
    # 3. Callback for Supervisor (Main Agent) - Ignore events tagged as 'sub_agent' to avoid duplication
    supervisor_callback = RedisStreamingCallback(redis_client, channel, source="supervisor", ignore_tags=["sub_agent"])

    # 1. Initialize Tools
    tools = []
    
    # Enable SQL Tool if datasource_id provided
    business_db_url = get_connection_string(datasource_id)
    
    if business_db_url:
        print(f"Initializing SQL Tool with: {business_db_url}")
        # Pass callback to tool
        sql_tool = create_sql_agent_tool(business_db_url, model, callbacks=[sql_agent_callback])
        tools.append(sql_tool)
    else:
        print("No Data Source configured. Agent will run without SQL capabilities.")

    # Enable Code Tool (Sandbox)
    print(f"Initializing Code Tool (Sandbox) with: {settings.SANDBOX_URL}")
    code_tool = create_code_agent_tool(settings.SANDBOX_URL, model, callbacks=[code_agent_callback])
    tools.append(code_tool)
    
    # 2. Setup Postgres Checkpointer
    # We need a connection pool for AsyncPostgresSaver
    
    # Use AsyncPostgresSaver.from_conn_string context manager
    async with AsyncPostgresSaver.from_conn_string(settings.POSTGRES_STATE_URL) as checkpointer:
        
        # Ensure tables exist (only need to run once, but safe to run here for MVP)
        await checkpointer.setup()
        
        supervisor = SupervisorAgent(
            model=model,
            tools=tools,
            checkpointer=checkpointer 
        )
        
        print(f"Agent starting for {session_id}, publishing to {channel}")
        
        try:
            # 4. Run Agent Workflow
            # Notify Frontend: Workflow Started
            await redis_client.publish(channel, AgentEvent(type=AgentEventType.AGENT_START, source="system").model_dump_json())
            
            # Execute the graph. 
            # All events (Streaming Tokens, Tool calls) will be captured by 'supervisor_callback' 
            # and 'sub_agent_callback' (which is wired into the sql_tool).
            await supervisor.ainvoke(
                user_input, 
                thread_id=session_id,
                config={"callbacks": [supervisor_callback]}
            )
            
            # Notify Frontend: Workflow Ended & Done
            await redis_client.publish(channel, AgentEvent(type=AgentEventType.AGENT_END, source="system").model_dump_json())
            
        except Exception as e:
            error_details = traceback.format_exc()
            print(f"Agent Error: {error_details}") # Print to worker logs
            
            # Send detailed error to frontend for debugging
            error_msg = AgentEvent(type=AgentEventType.ERROR, content=f"Error: {str(e)}", data={"traceback": error_details})
            await redis_client.publish(channel, error_msg.model_dump_json())
        finally:
            await redis_client.close()

@shared_task(bind=True)
def run_agent_workflow(self, agent_input_dict: dict):
    """
    Celery task to execute the Supervisor Agent workflow.
    Publishes events to Redis Pub/Sub for real-time streaming.
    """
    # Deserialize input
    try:
        agent_input = AgentInput(**agent_input_dict)
    except Exception as e:
        print(f"Invalid AgentInput: {e}")
        return {"status": "error", "error": str(e)}

    session_id = agent_input.session_id

    # Run the async agent logic in a new event loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(_run_agent_async(agent_input))
    finally:
        loop.close()
        
    return {"status": "finished", "session_id": session_id}
