from __future__ import annotations

from typing import Any
import uuid

from sqlalchemy.orm import Session

from app.node.core.base import BaseNode
from app.services.knowledge_base_service import search_kb_chunks
from deepeye.workflows.models import Node, Port
from deepeye.workflows.registry import NodeSpec


class KnowledgeSearchHandler:
    def __init__(self, db: Session, user_id) -> None:
        self.db = db
        self.user_id = user_id

    def execute(self, node: Node, inputs: dict[str, Any], context: object) -> dict[str, Any]:
        kb_ids_raw = inputs.get("kb_ids") or node.params.get("kb_ids")
        query = inputs.get("query") or node.params.get("query")
        top_k = int(node.params.get("top_k") or 5)

        if not kb_ids_raw:
            raise ValueError("kb_ids is required")
        if not query:
            raise ValueError("query is required")

        if isinstance(kb_ids_raw, str):
            kb_ids = [uuid.UUID(id.strip()) for id in kb_ids_raw.split(",") if id.strip()]
        elif isinstance(kb_ids_raw, list):
            kb_ids = [uuid.UUID(str(id)) for id in kb_ids_raw]
        else:
            raise ValueError("kb_ids must be a list or comma-separated string")

        results = search_kb_chunks(
            db=self.db,
            user_id=self.user_id,
            kb_ids=kb_ids,
            query=str(query),
            top_k=top_k
        )
        return {"results": results}


class KnowledgeSearchNode(BaseNode):
    node_type = "knowledge.search"

    @classmethod
    def spec(cls) -> NodeSpec:
        return NodeSpec(
            type=cls.node_type,
            description="Search the selected knowledge bases for relevant chunks.",
            params_schema={
                "kb_ids": {"type": "string", "required": False, "description": "Knowledge base ids as a comma-separated string. Prefer the `kb_ids` input edge when available."},
                "query": {"type": "string", "required": False, "description": "Search query."},
                "top_k": {"type": "integer", "required": False, "description": "Maximum number of chunks to return. Defaults to 5."},
            },
            inputs={
                "kb_ids": Port(schema="list[string]", required=False, description="Knowledge base ids to search."),
                "query": Port(schema="string", required=False, description="Search query.")
            },
            outputs={"results": Port(schema="list[dict]", description="Search results with content and metadata.")},
        )

    @classmethod
    def build_handler(cls, db: Session, user_id):
        return KnowledgeSearchHandler(db, user_id)
