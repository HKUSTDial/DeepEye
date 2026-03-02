"""
Max/Min Checker - MAX/MIN聚合函数检查器

检查并修正MAX/MIN函数的错误使用
"""

import logging
import re
from typing import Dict, Tuple, Optional, List

from langchain_core.language_models import BaseChatModel

from deepeye.datasource.datasource import DatabaseMetadata
from deepeye.agents.nl2sql.sql_revision.base import BaseChecker
from deepeye.agents.nl2sql.sql_revision.prompt import COMMON_CHECKER_PROMPT
from deepeye.agents.nl2sql.utils.schema_utils import get_database_schema_profile

logger = logging.getLogger(__name__)


class MaxMinChecker(BaseChecker):
    """
    MAX/MIN检查器：检查并修正聚合函数的错误使用
    
    常见问题：
    - WHERE col = (SELECT MAX/MIN(col) FROM table) 应改为 ORDER BY + LIMIT
    - SELECT MAX/MIN(col) ... LIMIT 1 中的MAX/MIN是多余的
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
        """检查MAX/MIN使用并修正"""
        suggestion = self._check_max_min(sql)

        if not suggestion:
            return sql, {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

        logger.info(f"[MaxMinChecker] Found max/min issues in SQL")

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

    def _check_max_min(self, sql: str) -> Optional[str]:
        """
        检查MAX/MIN使用问题
        
        Returns:
            修改建议列表，如果没有问题返回None
        """
        identifier = r'(?:`[^`]+`|\[[^\]]+\]|"[^"]+"|[\w\.]+)'
        suggestions: List[str] = []

        # 模式1: WHERE col = (SELECT MAX/MIN(col) FROM table)
        max_min_pattern = re.compile(
            rf"=\s*\(\s*SELECT\s*(MAX|MIN)\s*\(\s*({identifier})\s*\)\s*FROM\s*({identifier})",
            re.IGNORECASE | re.DOTALL
        )
        for match in max_min_pattern.findall(sql):
            func, col, table = match
            order = "DESC" if func.upper() == "MAX" else "ASC"
            suggestions.append(
                f"Replace 'WHERE {col} = (SELECT {func}({col}) FROM {table})' "
                f"with 'ORDER BY {col} {order} LIMIT 1'"
            )

        # 模式2: = (SELECT ... LIMIT 1) 嵌套查询
        order_amb = set(re.findall(
            r"= (\(SELECT .* LIMIT \d\))",
            sql,
            re.IGNORECASE | re.DOTALL
        ))
        for match in order_amb:
            suggestions.append(f"Replace nested subquery '{match}' with JOIN")

        # 模式3: SELECT MAX/MIN(col) ... LIMIT 1 （MAX/MIN多余）
        select_amb_pattern = re.compile(
            rf"^SELECT[^\(\)]*? ((MIN|MAX)\(\s*{identifier}\s*\)).*?LIMIT 1",
            re.IGNORECASE | re.DOTALL | re.MULTILINE
        )
        for match in select_amb_pattern.findall(sql):
            suggestions.append(
                f"'{match[0]}' is redundant with LIMIT 1. "
                f"Use ORDER BY + LIMIT instead of {match[1]} function"
            )

        if suggestions:
            return "\n".join([f"{i + 1}. {s}" for i, s in enumerate(suggestions)])

        return None
