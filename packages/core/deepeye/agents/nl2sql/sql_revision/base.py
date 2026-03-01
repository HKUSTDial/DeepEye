"""
SQL Revision Base - SQL检查器基类
"""

import logging
import re
from abc import ABC, abstractmethod
from typing import Dict, List, Tuple, Optional

from langchain_core.language_models import BaseChatModel

from deepeye.datasource.datasource import DatabaseMetadata
from deepeye.agents.nl2sql.utils.llm_extractor import LLMExtractor

logger = logging.getLogger(__name__)


class BaseChecker(ABC):
    """SQL检查器抽象基类"""

    def __init__(self, fix_end_token: bool = True):
        """
        初始化检查器

        Args:
            fix_end_token: 是否自动修复缺失的结束标签
        """
        self.fix_end_token = fix_end_token
        self.extractor = LLMExtractor()

    @abstractmethod
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
        检查并修正SQL

        Args:
            sql: 待检查的SQL语句
            metadata: 数据库元数据
            llm: 语言模型
            database_path: 数据库路径（用于执行验证）
            question: 原始问题
            evidence: 提示信息
            sampling_budget: 采样次数

        Returns:
            (修正后的SQL, token使用统计)
        """
        pass

    def _parse_llm_response(self, response: str) -> Optional[str]:
        """
        解析LLM响应，提取SQL语句

        Args:
            response: LLM原始响应

        Returns:
            提取的SQL语句，解析失败返回None
        """
        try:
            answer_match = re.search(r"<r>(.*?)</r>", response, re.DOTALL)
            if not answer_match:
                logger.warning("No result tag found in LLM response")
                return None

            answer_content = answer_match.group(1).strip()

            # 去除可能的代码块标记
            if answer_content.startswith("```sql") and answer_content.endswith("```"):
                answer_content = answer_content[len("```sql"):-len("```")].strip()
            elif answer_content.startswith("```") and answer_content.endswith("```"):
                answer_content = answer_content[3:-3].strip()

            return answer_content

        except Exception as e:
            logger.error(f"Error parsing LLM response: {e}")
            return None
