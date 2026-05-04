"""Workflow engine setup and handlers."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.node import register_node_handlers, register_node_specs
from deepeye.workflows import ExecutionEngine, NodeRegistry
from deepeye.workflows.engine import ConditionHandler, TransformHandler


class AlwaysTrueCondition(ConditionHandler):
    def evaluate(self, value: Any, context: object) -> bool:
        return True


class IdentityTransform(TransformHandler):
    def apply(self, value: Any, context: object) -> Any:
        return value


def _schema_check(source_schema: Any, target_schema: Any) -> bool:
    if source_schema is None or target_schema is None:
        return True
    if source_schema == "any" or target_schema == "any":
        return True
    return source_schema == target_schema


def build_registry() -> NodeRegistry:
    registry = NodeRegistry()
    register_node_specs(registry)
    return registry


def build_engine(db: Session, user_id, sandbox=None, session_id: str | None = None, model=None) -> ExecutionEngine:
    registry = build_registry()
    engine = ExecutionEngine(node_registry=registry, schema_check=_schema_check)
    register_node_handlers(engine, db, user_id, sandbox=sandbox, session_id=session_id, model=model)
    engine.register_condition("always", AlwaysTrueCondition())
    engine.register_transform("identity", IdentityTransform())
    return engine
