"""Workflow node registry discovery."""

from __future__ import annotations

import importlib
import inspect
from typing import Iterable

from app.node.core.base import BaseNode
from deepeye.workflows.engine import ExecutionEngine
from deepeye.workflows.registry import NodeRegistry

# Keep registry discovery explicit so folder reorganization does not change
# node loading behavior implicitly.
NODE_MODULES: tuple[str, ...] = (
    "app.node.data.datasource_read",
    "app.node.data.sql_execute",
    "app.node.rows.basic",
    "app.node.llm.answer",
    "app.node.code.python_code",
    "app.node.dashboard.node",
    "app.node.video.node",
    "app.node.report.node",
)


def _iter_modules() -> Iterable[object]:
    for module_name in NODE_MODULES:
        yield importlib.import_module(module_name)


def _iter_nodes() -> Iterable[type[BaseNode]]:
    seen: set[type[BaseNode]] = set()
    for _ in _iter_modules():
        for node_cls in BaseNode.__subclasses__():
            if not node_cls.__module__.startswith("app.node."):
                continue
            if node_cls in seen:
                continue
            seen.add(node_cls)
            yield node_cls


def register_node_specs(registry: NodeRegistry) -> None:
    for node_cls in _iter_nodes():
        registry.register(node_cls.spec())


def register_node_handlers(engine: ExecutionEngine, db, user_id, sandbox=None, session_id: str | None = None, model=None) -> None:
    for node_cls in _iter_nodes():
        build_handler = node_cls.build_handler
        handler = None
        try:
            sig = inspect.signature(build_handler)
            kwargs = {}
            if "sandbox" in sig.parameters:
                kwargs["sandbox"] = sandbox
            if "session_id" in sig.parameters:
                kwargs["session_id"] = session_id
            if "model" in sig.parameters:
                kwargs["model"] = model
            handler = build_handler(db, user_id, **kwargs)
        except TypeError:
            handler = build_handler(db, user_id)
        if handler is not None:
            engine.register_handler(node_cls.node_type, handler)
