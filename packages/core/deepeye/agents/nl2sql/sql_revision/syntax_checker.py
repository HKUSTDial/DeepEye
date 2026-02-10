"""
Syntax Checker - SQL语法检查器

检查SQL是否可以正确执行，如果出错则尝试修正
"""

import logging
from typing import Dict, List, Tuple
from collections import Counter

from langchain_core.language_models import BaseChatModel

from deepeye.datasource.datasource import DatabaseMetadata
from deepeye.agents.nl2sql.sql_revision.base import BaseChecker
from deepeye.agents.nl2sql.sql_revision.prompt import EXECUTION_CHECKER_PROMPT
from deepeye.agents.nl2sql.utils.schema_utils import get_database_schema_profile
from deepeye.agents.nl2sql.utils.db_utils import execute_sql

logger = logging.getLogger(__name__)


class SyntaxChecker(BaseChecker):
    """
    语法检查器：执行SQL并检查是否有语法错误
    
    如果执行失败，使用LLM尝试修正
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
        """检查SQL语法并修正"""
        if not database_path:
            return sql, {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

        execution_result = execute_sql(database_path, sql)

        # 执行成功，无需修正
        if execution_result.result_type in ["success", "empty_result", "all_null_result"]:
            return sql, {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

        # 执行失败，需要修正
        logger.info(f"[SyntaxChecker] SQL execution failed: {execution_result.error_message}")

        database_schema_profile = get_database_schema_profile(metadata)
        prompt = EXECUTION_CHECKER_PROMPT.format(
            DATABASE_SCHEMA=database_schema_profile,
            QUESTION=question,
            HINT=evidence or "No hint provided.",
            QUERY=sql,
            RESULT=execution_result.result_table_str or execution_result.error_message
        )

        results, token_usage = await self.extractor.extract_with_retry(
            llm=llm,
            messages=[{"role": "user", "content": prompt}],
            rule_parser=self._parse_llm_response,
            fix_end_token=self.fix_end_token,
            end_token="</r>",
            n=sampling_budget
        )

        if results:
            best_sql = self._select_best_candidate(results, database_path)
            return best_sql, token_usage

        return sql, token_usage

    def _select_best_candidate(self, candidates: List[str], database_path: str) -> str:
        """
        从多个候选中选择最佳SQL
        
        优先选择执行成功且结果一致性高的SQL
        """
        valid_candidates = []

        for sql in candidates:
            if not sql:
                continue
            result = execute_sql(database_path, sql)
            if result.result_type in ["success", "empty_result", "all_null_result"]:
                result_key = frozenset(result.result_rows or [])
                valid_candidates.append((sql, result_key))

        if not valid_candidates:
            return candidates[0] if candidates else ""

        # 选择结果出现次数最多的SQL
        counter = Counter(r for _, r in valid_candidates)
        return max(valid_candidates, key=lambda x: counter[x[1]])[0]
