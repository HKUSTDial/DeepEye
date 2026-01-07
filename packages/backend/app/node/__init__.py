"""Workflow node registry discovery."""

from __future__ import annotations

import importlib
import pkgutil
import inspect
from typing import Iterable

from app.node.base import BaseNode
from deepeye.workflows.engine import ExecutionEngine
from deepeye.workflows.registry import NodeRegistry


_DISABLED_NODE_TYPES = {
    # Legacy data-analysis helpers are disabled to avoid bloating the prompt;
    # keep workflows focused on python.code for now.
    "data.aggregate",
    "data.filter_rows",
    "data.limit_rows",
    "data.select_columns",
    "data.sort_rows",
    # "datasource.read",
    # sql.execute is enabled to allow SQL+Python workflows
    "stats.correlation",
    "stats.summary",
}


def _iter_modules() -> Iterable[object]:
    for module_info in pkgutil.iter_modules(__path__, __name__ + "."):
        yield importlib.import_module(module_info.name)


def _iter_nodes() -> Iterable[type[BaseNode]]:
    seen: set[type[BaseNode]] = set()
    for _ in _iter_modules():
        for node_cls in BaseNode.__subclasses__():
            if node_cls in seen:
                continue
            if node_cls.node_type.startswith("viz."):
                continue
            if node_cls.node_type in _DISABLED_NODE_TYPES:
                continue
            seen.add(node_cls)
            yield node_cls


def register_node_specs(registry: NodeRegistry) -> None:
    for node_cls in _iter_nodes():
        registry.register(node_cls.spec())


def register_node_handlers(engine: ExecutionEngine, db, user_id, sandbox=None) -> None:
    for node_cls in _iter_nodes():
        build_handler = node_cls.build_handler
        handler = None
        try:
            sig = inspect.signature(build_handler)
            if "sandbox" in sig.parameters:
                handler = build_handler(db, user_id, sandbox=sandbox)
            else:
                handler = build_handler(db, user_id)
        except TypeError:
            handler = build_handler(db, user_id)
        if handler is not None:
            engine.register_handler(node_cls.node_type, handler)
