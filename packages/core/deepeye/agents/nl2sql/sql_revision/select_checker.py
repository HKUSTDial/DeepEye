"""
Select Checker - SELECT语句检查器

检查并修正SELECT语句中的问题
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


class SelectChecker(BaseChecker):
    """
    SELECT检查器
    
    检查并修正SELECT语句中的问题：
    - SELECT table.* 应替换为具体列名
    - 字符串连接 || ' ' || 应替换为逗号
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
        """检查SELECT并修正"""
        # 先处理字符串连接（无需LLM）
        sql = sql.replace("|| ' ' ||", ', ')

        suggestion = self._check_select(sql)

        if not suggestion:
            return sql, {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

        logger.info(f"[SelectChecker] Found select issues in SQL")

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

    def _check_select(self, sql: str) -> Optional[str]:
        """
        检查SELECT语句中的问题
        """
        identifier = r'(?:`[^`]+`|\[[^\]]+\]|"[^"]+"|[\w\.]+)'

        # 检查 SELECT table.* 模式
        select_amb = re.findall(
            rf"^SELECT.*? ({identifier}\.\*).*?FROM",
            sql,
            re.IGNORECASE | re.DOTALL | re.MULTILINE
        )

        if select_amb:
            suggestions = [
                f"Replace '{match}' with specific column names (e.g., table.id, table.name)"
                for match in select_amb
            ]
            return "\n".join([f"{i + 1}. {s}" for i, s in enumerate(suggestions)])

        return None
