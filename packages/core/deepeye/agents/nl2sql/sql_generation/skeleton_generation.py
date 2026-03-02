"""
Plan(规划) - Skeleton(生成骨架) - Complete(生成)
"""

import logging
from typing import List, Any, Dict, Tuple, Union, Optional

from langchain_core.language_models import BaseChatModel

from deepeye.datasource.datasource import DatabaseMetadata

from deepeye.agents.nl2sql.sql_generation.base import BaseSQLGenerator
from deepeye.agents.nl2sql.utils.llm_extractor import LLMExtractor
from deepeye.agents.nl2sql.utils.schema_utils import get_database_schema_profile

from deepeye.agents.nl2sql.sql_generation.prompt import SKELETON_SQL_GENERATION_PROMPT

logger = logging.getLogger(__name__)


class SkeletonGenerator(BaseSQLGenerator):
    """
    Divide - Conquer SQL生成器
    使用递归分而治之将复杂问题拆分为子问题，从而逐步的生成SQL
    """

    def __init__(self, fix_end_token: bool = True):
        self.fix_end_token = fix_end_token
        self.extractor = LLMExtractor()

    async def generate(
            self,
            question: str,
            metadata: DatabaseMetadata,
            llm: BaseChatModel,
            sampling_budget: int = 1,
            **kwargs
    ) -> Tuple[List[str], Dict[str, int]]:
        """
        使用DC方法来生成SQL
        """

        if sampling_budget == 0:
            return [], {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

        # 获取到数据库的元数据信息
        database_schema_profile = get_database_schema_profile(metadata=metadata)

        prompt = SKELETON_SQL_GENERATION_PROMPT.format(
            DATABASE_SCHEMA=database_schema_profile,
            QUESTION=question
        ).strip()

        all_sql_candidates, total_token_usage = await self.extractor.extract_with_retry(
            llm=llm,
            messages=[{"role": "user", "content": prompt}],
            n=sampling_budget,
            fix_end_token=self.fix_end_token,
            rule_parser=self._parse_llm_response,
            end_token="</result>"
        )

        return all_sql_candidates, total_token_usage



