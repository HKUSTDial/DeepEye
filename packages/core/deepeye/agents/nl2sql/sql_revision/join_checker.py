"""
Join Checker - JOIN语法检查器

检查并修正SQL中的JOIN语法问题
"""

import logging
import re
from typing import Dict, Tuple, Optional

from langchain_core.language_models import BaseChatModel

from deepeye.datasource.datasource import DatabaseMetadata
from deepeye.agents.nl2sql.sql_revision.base import BaseChecker
from deepeye.agents.nl2sql.sql_revision.prompt import COMMON_CHECKER_PROMPT
from deepeye.agents.nl2sql.utils.schema_utils import get_database_schema_profile

logger = logging.getLogger(__name__)


class JoinChecker(BaseChecker):
    """
    JOIN检查器：检查并修正JOIN语法问题
    
    常见问题：
    - JOIN ON 使用 OR 连接多个条件
    - JOIN ON 使用 IN 子句
    """

    async def check_and_revise(
            self,
            sql: str,
            metadata: DatabaseMetadata,
            llm: BaseChatModel,
            database_path: str = None,
            question: str = "",
            evidence: str = "",
            sampling_budget: int = 1
    ) -> Tuple[str, Dict[str, int]]:
        """检查JOIN语法并修正"""
        suggestion = self._check_join(sql)

        if not suggestion:
            return sql, {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

        logger.info(f"[JoinChecker] Found join issues in SQL")

        database_schema_profile = get_database_schema_profile(metadata)
        prompt = COMMON_CHECKER_PROMPT.format(
            DATABASE_SCHEMA=database_schema_profile,
            QUESTION=question,
            HINT=evidence or "No hint provided.",
            QUERY=sql,
            SUGGESTIONS=suggestion
        )

        results, token_usage = await self.extractor.extract_with_retry(
            llm=llm,
            messages=[{"role": "user", "content": prompt}],
            rule_parser=self._parse_llm_response,
            fix_end_token=self.fix_end_token,
            end_token="</r>",
            n=1
        )

        if results:
            return results[0], token_usage

        return sql, token_usage

    def _check_join(self, sql: str) -> Optional[str]:
        """
        检查JOIN语法问题
        
        Returns:
            修改建议，如果没有问题返回None
        """
        identifier = r'(?:`[^`]+`|\[[^\]]+\]|"[^"]+"|[\w\.]+)'

        # 检查 JOIN ... ON ... OR 或 JOIN ... ON ... IN 的模式
        join_pattern = re.compile(
            rf"JOIN\s+{identifier}(\s+AS\s+{identifier}){{0,1}}\s+ON(\s+{identifier}\.{identifier}\s*(=\s*{identifier}\.{identifier}(?:\s+OR\s+{identifier}\.{identifier}\s*=\s*{identifier}\.{identifier})+|IN\s+\(.*?\)))",
            re.IGNORECASE | re.DOTALL
        )

        if join_pattern.findall(sql):
            return (
                "The SQL uses JOIN incorrectly with OR or IN in the ON clause. "
                "Please keep only the highest priority equality condition "
                "(e.g., `Ta.column = Tb.column`) and remove OR/IN conditions."
            )

        return None
