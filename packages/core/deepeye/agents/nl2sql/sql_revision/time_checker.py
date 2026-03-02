"""
Time Checker - 时间格式检查器

检查并修正SQL中的时间格式问题（无需LLM）
"""

import logging
import re
from typing import Dict, Tuple, Optional

from langchain_core.language_models import BaseChatModel

from deepeye.datasource.datasource import DatabaseMetadata
from deepeye.agents.nl2sql.sql_revision.base import BaseChecker

logger = logging.getLogger(__name__)


class TimeChecker(BaseChecker):
    """
    时间格式检查器
    
    检查并修正时间比较中的格式问题，如strftime比较时缺少引号
    
    这个检查器不需要LLM，直接通过正则表达式修正
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
        """
        检查时间格式并修正
        
        Note: 此检查器不消耗token
        """
        revised_sql = self._check_time(sql)

        if revised_sql and revised_sql != sql:
            logger.info(f"[TimeChecker] Fixed time format in SQL")
            return revised_sql, {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

        return sql, {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

    def _check_time(self, sql: str) -> Optional[str]:
        """
        检查并修正时间格式问题
        
        修正 strftime(...) >= 2020 为 strftime(...) >= '2020'
        """
        # 修正strftime比较中缺少引号的数字
        revised = re.sub(
            r"(strftime *\([^\(]*?\) *[>=<]+ *)(\d{4,})",
            r"\1'\2'",
            sql
        )

        if revised != sql:
            return revised

        return None
