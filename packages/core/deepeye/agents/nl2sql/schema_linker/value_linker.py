"""
Value Linker - 基于值检索结果的Schema链接器
"""

import logging
from typing import Dict, List, Tuple
from collections import defaultdict

from langchain_core.language_models import BaseChatModel

from deepeye.datasource.datasource import DatabaseMetadata
from deepeye.agents.nl2sql.schema_linker.base import BaseSchemaLinker
from deepeye.agents.nl2sql.utils.schema_utils import (
    map_lower_table_name_to_original,
    map_lower_column_name_to_original,
)

logger = logging.getLogger(__name__)


class ValueLinker(BaseSchemaLinker):
    """
    基于值检索结果的Schema链接器

    通过检查检索到的值的距离来确定哪些表和列与问题相关
    """

    def __init__(self, value_distance_threshold: float = 0.3):
        """
        初始化值链接器

        Args:
            value_distance_threshold: 值距离阈值，低于此阈值的值被认为相关
        """
        self.value_distance_threshold = value_distance_threshold

    async def link(
            self,
            question: str,
            metadata: DatabaseMetadata,
            llm: BaseChatModel,
            retrieved_values: Dict[str, Dict[str, List[Dict]]] = None,
            **kwargs
    ) -> Tuple[Dict[str, List[str]], Dict[str, int]]:
        """
        基于值检索结果链接表和列

        Args:
            question: 用户问题
            metadata: 数据库元数据
            llm: 语言模型（此链接器不使用）
            retrieved_values: 值检索结果

        Returns:
            链接的表和列字典，以及token使用统计
        """
        if not retrieved_values:
            return {}, {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

        linked_tables_and_columns = defaultdict(list)

        for table_name, columns in retrieved_values.items():
            # 映射到原始表名
            original_table_name = map_lower_table_name_to_original(
                table_name.lower(), metadata
            )
            if original_table_name is None:
                continue

            for column_name, values in columns.items():
                # 检查是否有距离低于阈值的值
                if any(value["distance"] < self.value_distance_threshold for value in values):
                    # 映射到原始列名
                    original_column_name = map_lower_column_name_to_original(
                        original_table_name, column_name.lower(), metadata
                    )
                    if original_column_name is None:
                        continue
                    linked_tables_and_columns[original_table_name].append(original_column_name)

        return dict(linked_tables_and_columns), {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}


