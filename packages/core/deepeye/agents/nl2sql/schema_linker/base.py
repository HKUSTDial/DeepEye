from abc import ABC, abstractmethod
from deepeye.datasource.datasource import DatabaseMetadata

from langchain_core.language_models import BaseChatModel


class BaseSchemaLinker:

    @abstractmethod
    def link(self, question: str, datasource: DatabaseMetadata, llm: BaseChatModel):
        raise NotImplementedError
