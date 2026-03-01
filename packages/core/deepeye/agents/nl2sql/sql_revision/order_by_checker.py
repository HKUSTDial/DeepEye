"""
Order By Checker - ORDER BY语法检查器

检查并修正ORDER BY相关的问题
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


class OrderByLimitChecker(BaseChecker):
    """
    ORDER BY LIMIT检查器
    
    检查 ORDER BY MIN/MAX(col) LIMIT 的错误模式
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
        """检查ORDER BY LIMIT并修正"""
        suggestion = self._check_order_by_limit(sql)

        if not suggestion:
            return sql, {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

        logger.info(f"[OrderByLimitChecker] Found order by limit issues")

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

    def _check_order_by_limit(self, sql: str) -> Optional[str]:
        """
        检查ORDER BY中使用MIN/MAX的问题
        """
        identifier = r'(?:`[^`]+`|\[[^\]]+\]|"[^"]+"|[\w\.]+)'
        pattern = re.compile(
            rf"ORDER BY ((MIN|MAX)\(\s*({identifier})\s*\)).*? LIMIT \d+",
            re.IGNORECASE | re.DOTALL
        )

        match = pattern.search(sql)
        if match:
            return (
                f"Using MIN/MAX in ORDER BY clause is incorrect: '{match.group()}'. "
                f"If the SQL contains GROUP BY, consider using SUM({match.group(3)}) instead. "
                f"Otherwise, use simple column name with ORDER BY + LIMIT."
            )

        return None


class OrderByNullChecker(BaseChecker):
    """
    ORDER BY NULL检查器
    
    检查ORDER BY + LIMIT时是否需要添加IS NOT NULL条件
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
        """检查ORDER BY NULL问题并修正"""
        suggestion = self._check_order_by_null(sql)

        if not suggestion:
            return sql, {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

        logger.info(f"[OrderByNullChecker] Found order by null issues")

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

    def _check_order_by_null(self, sql: str) -> Optional[str]:
        """
        检查ORDER BY列是否需要NULL处理
        """
        # 查找 ORDER BY ... LIMIT 模式（不含DESC）
        matches = re.findall(
            r"ORDER BY .*?(?<!DESC )LIMIT +\d+;{0,1}",
            sql,
            re.IGNORECASE
        )

        if not matches:
            return None

        # 如果包含聚合函数，则不需要NULL检查
        for match in matches:
            if re.findall(r"SUM\(|COUNT\(", match, re.IGNORECASE):
                return None

        suggestions = []
        for match in matches:
            suggestions.append(
                f"Add `IS NOT NULL` condition in WHERE clause for ORDER BY column: {match}"
            )

        return "\n".join(suggestions) if suggestions else None
