from __future__ import annotations

import json
from typing import Any

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from app.core.config import settings
from app.node.core.base import BaseNode
from app.workflow.services.datasets import compact_value_for_transport, dataset_ref_columns, dataset_ref_preview, is_dataset_ref
from deepeye.workflows.models import Node, Port
from deepeye.workflows.registry import NodeSpec

_MAX_ROWS = 20


def _safe_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, default=str)


class LLMAnswerHandler:
    def __init__(self, model: BaseChatModel | None = None) -> None:
        self._model = model

    def _resolve_model(self) -> BaseChatModel:
        if self._model is None:
            self._model = ChatOpenAI(
                api_key=settings.LLM_API_KEY,
                base_url=settings.LLM_BASE_URL,
                model=settings.LLM_MODEL,
                temperature=0.2,
                streaming=False,
            )
        return self._model

    def execute(self, node: Node, inputs: dict[str, Any], context: object) -> dict[str, Any]:
        del context
        question = node.params.get("question")
        if not question:
            raise ValueError("question is required")

        context_input = inputs.get("context")
        artifacts = inputs.get("artifacts")
        dataset_ref = inputs.get("dataset_ref")
        rows = dataset_ref_preview(dataset_ref, limit=_MAX_ROWS) if is_dataset_ref(dataset_ref) else None

        prompt = (
            "You are a workflow answer node.\n"
            "Use only the provided workflow context to answer the user's question.\n"
            "If evidence is missing, say so clearly and briefly.\n"
            "Keep the answer concise and in the user's language.\n"
        )

        payload = {
            "question": question,
            "rows": rows,
            "context": context_input,
            "artifacts": artifacts,
            "dataset_ref": (
                {
                    "path": dataset_ref.get("path"),
                    "format": dataset_ref.get("format"),
                    "row_count": dataset_ref.get("row_count"),
                    "columns": dataset_ref_columns(dataset_ref),
                    "preview_rows": dataset_ref_preview(dataset_ref, limit=10),
                }
                if is_dataset_ref(dataset_ref)
                else None
            ),
        }
        payload = compact_value_for_transport(payload, row_limit=10, text_limit=3000)
        response = self._resolve_model().invoke(
            [
                SystemMessage(content=prompt),
                HumanMessage(content=_safe_json(payload)),
            ]
        )
        content = getattr(response, "content", "")
        answer = content if isinstance(content, str) else str(content)
        return {"answer": answer.strip()}


class LLMAnswerNode(BaseNode):
    node_type = "llm.answer"

    @classmethod
    def spec(cls) -> NodeSpec:
        return NodeSpec(
            type=cls.node_type,
            description="Generate the final user-facing text answer from workflow results.",
            params_schema={
                "question": {"type": "string", "required": True, "description": "User question or final answer target."},
            },
            inputs={
                "dataset_ref": Port(schema="dict", required=False, description="Primary dataset to ground the answer."),
                "context": Port(schema="any", required=False, multiple=True, description="Optional structured context from upstream nodes."),
                "artifacts": Port(schema="list[dict]", required=False, multiple=True, description="Optional artifact metadata to mention when relevant."),
            },
            outputs={"answer": Port(schema="string", required=True, description="Final grounded answer for the user.")},
        )

    @classmethod
    def build_handler(cls, db, user_id, model: BaseChatModel | None = None):
        del db, user_id
        return LLMAnswerHandler(model=model)
