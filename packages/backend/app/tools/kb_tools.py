from __future__ import annotations

import uuid

from deepeye.tools.base import tool

from app.core.config import settings
from app.services.knowledge_base_service import search_kb_chunks
from app.services.agent_prompts import build_knowledge_base_prompt
from app.db.session import SessionLocal
from deepeye.agents import KnowledgeBaseAgent
from sqlalchemy import text


def create_search_kb_tool(user_id: str, kb_ids: list[str] | None) -> callable:
    user_uuid = None
    try:
        user_uuid = uuid.UUID(user_id)
    except (TypeError, ValueError):
        user_uuid = None

    @tool
    async def search_kb(query: str, top_k: int = 5) -> dict:
        """
        Search knowledge base content for the given query.

        Args:
            query: search query string
            top_k: max number of chunks to return
        """
        if not user_uuid:
            return {"status": "error", "error": "User not found."}
        if not kb_ids:
            return {"status": "error", "error": "No knowledge bases selected."}
        try:
            kb_uuid_list = [uuid.UUID(kb_id) for kb_id in kb_ids]
        except Exception:
            return {"status": "error", "error": "Invalid knowledge base ids."}
        db = SessionLocal()
        try:
            results = search_kb_chunks(db, user_uuid, kb_uuid_list, query, top_k=top_k)
            return {"status": "success", "results": results}
        finally:
            db.close()

    return search_kb


def create_kb_sql_tool(user_id: str, kb_ids: list[str] | None) -> callable:
    user_uuid = None
    try:
        user_uuid = uuid.UUID(user_id)
    except (TypeError, ValueError):
        user_uuid = None

    @tool
    async def execute_kb_sql(query: str, limit: int = 10) -> dict:
        """
        Execute a read-only SQL query over knowledge base tables.

        Requirements:
        - SELECT only, no writes.
        - Must include :user_id and :kb_ids parameters in WHERE clause.
        - Use knowledge_base_chunks / knowledge_base_files / knowledge_bases only.
        """
        if not user_uuid:
            return {"status": "error", "error": "User not found."}
        if not kb_ids:
            return {"status": "error", "error": "No knowledge bases selected."}
        try:
            kb_uuid_list = [uuid.UUID(kb_id) for kb_id in kb_ids]
        except Exception:
            return {"status": "error", "error": "Invalid knowledge base ids."}

        normalized = " ".join(query.strip().split()).lower()
        if not normalized.startswith("select"):
            return {"status": "error", "error": "Only SELECT queries are allowed."}
        if ";" in normalized:
            return {"status": "error", "error": "Multi-statement queries are not allowed."}
        forbidden = ["insert", "update", "delete", "drop", "alter", "create", "grant", "revoke", "truncate"]
        if any(token in normalized for token in forbidden):
            return {"status": "error", "error": "Write operations are not allowed."}
        if "knowledge_base" not in normalized:
            return {"status": "error", "error": "Query must target knowledge base tables."}
        if ":user_id" not in normalized or ":kb_ids" not in normalized:
            return {
                "status": "error",
                "error": "Query must include :user_id and :kb_ids filters.",
            }

        if " limit " not in f" {normalized} ":
            query = f"{query.strip()} LIMIT :limit"

        db = SessionLocal()
        try:
            result = db.execute(
                text(query),
                {"user_id": user_uuid, "kb_ids": kb_uuid_list, "limit": limit},
            )
            rows = [dict(row._mapping) for row in result.fetchall()]
            return {"status": "success", "rows": rows}
        except Exception as exc:
            return {"status": "error", "error": str(exc)}
        finally:
            db.close()

    return execute_kb_sql


def create_knowledge_base_agent_tool(
    model,
    session_id: str,
    user_id: str,
    kb_ids: list[str] | None,
    callbacks: list | None = None,
) -> callable:
    @tool
    async def query_knowledge_base(question: str) -> str:
        """
        Answer questions using the selected knowledge bases.
        """
        kb_agent = KnowledgeBaseAgent(
            model=model,
            tools=[create_kb_sql_tool(user_id, kb_ids)],
            system_prompt=build_knowledge_base_prompt(),
        )
        result = await kb_agent.ainvoke(
            question,
            thread_id=f"kb_agent_{session_id}",
            config={"callbacks": callbacks},
        )
        messages = result.get("messages", [])
        return messages[-1].content if messages else ""

    return query_knowledge_base
