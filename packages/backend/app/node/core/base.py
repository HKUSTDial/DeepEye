from __future__ import annotations

from abc import ABC, abstractmethod

from deepeye.workflows.engine import NodeHandler
from deepeye.workflows.registry import NodeSpec


class BaseNode(ABC):
    node_type: str

    @classmethod
    @abstractmethod
    def spec(cls) -> NodeSpec:
        raise NotImplementedError

    @classmethod
    def build_handler(cls, db, user_id) -> NodeHandler | None:
        return None
