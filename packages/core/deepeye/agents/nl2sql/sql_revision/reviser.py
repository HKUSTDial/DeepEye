"""
SQL Reviser - SQL修正器

整合所有checker，提供统一的SQL修正接口
"""

import logging
from typing import Dict, List, Tuple

from langchain_core.language_models import BaseChatModel

from deepeye.datasource.datasource import DatabaseMetadata
from deepeye.agents.nl2sql.sql_revision.base import BaseChecker
from deepeye.agents.nl2sql.sql_revision.syntax_checker import SyntaxChecker
from deepeye.agents.nl2sql.sql_revision.join_checker import JoinChecker
from deepeye.agents.nl2sql.sql_revision.max_min_checker import MaxMinChecker
from deepeye.agents.nl2sql.sql_revision.order_by_checker import OrderByLimitChecker, OrderByNullChecker
from deepeye.agents.nl2sql.sql_revision.time_checker import TimeChecker
from deepeye.agents.nl2sql.sql_revision.select_checker import SelectChecker

logger = logging.getLogger(__name__)


class SQLReviser:
    """
    SQL修正器：组合多个checker来修正SQL
    
    默认checker顺序：
    1. SyntaxChecker - 语法检查（最重要，放在第一位）
    2. JoinChecker - JOIN语法检查
    3. MaxMinChecker - MAX/MIN函数检查
    4. OrderByLimitChecker - ORDER BY LIMIT检查
    5. TimeChecker - 时间格式检查（无需LLM）
    6. SelectChecker - SELECT语句检查
    7. OrderByNullChecker - ORDER BY NULL检查
    """

    def __init__(
            self,
            fix_end_token: bool = True,
            custom_checkers: List[BaseChecker] = None
    ):
        """
        初始化SQL修正器

        Args:
            fix_end_token: 是否自动修复LLM响应中缺失的结束标签
            custom_checkers: 自定义checker列表，如果提供则使用自定义列表
        """
        self.fix_end_token = fix_end_token

        if custom_checkers is not None:
            self.checkers = custom_checkers
        else:
            # 默认checker顺序
            self.checkers: List[BaseChecker] = [
                SyntaxChecker(fix_end_token),
                JoinChecker(fix_end_token),
                MaxMinChecker(fix_end_token),
                OrderByLimitChecker(fix_end_token),
                TimeChecker(fix_end_token),
                SelectChecker(fix_end_token),
                OrderByNullChecker(fix_end_token),
            ]

    async def revise(
            self,
            sql: str,
            metadata: DatabaseMetadata,
            llm: BaseChatModel,
            database_path: str = None,
            question: str = "",
            evidence: str = ""
    ) -> Tuple[str, Dict[str, int]]:
        """
        依次应用所有checker修正SQL

        Args:
            sql: 原始SQL语句
            metadata: 数据库元数据
            llm: 语言模型
            database_path: 数据库路径（用于执行验证）
            question: 原始问题
            evidence: 提示信息

        Returns:
            (修正后的SQL, token使用统计)
        """
        total_tokens = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        current_sql = sql

        for checker in self.checkers:
            checker_name = checker.__class__.__name__

            try:
                revised_sql, tokens = await checker.check_and_revise(
                    current_sql,
                    metadata,
                    llm,
                    database_path,
                    question,
                    evidence
                )

                # 累加token统计
                for key in total_tokens:
                    total_tokens[key] += tokens.get(key, 0)

                # 如果有修改，记录日志
                if revised_sql != current_sql:
                    logger.debug(f"[{checker_name}] SQL revised")
                    current_sql = revised_sql

            except Exception as e:
                logger.error(f"[{checker_name}] Error during check: {e}")
                # 继续执行其他checker

        return current_sql, total_tokens

    def add_checker(self, checker: BaseChecker, position: int = None):
        """
        添加自定义checker

        Args:
            checker: checker实例
            position: 插入位置，None表示添加到末尾
        """
        if position is None:
            self.checkers.append(checker)
        else:
            self.checkers.insert(position, checker)

    def remove_checker(self, checker_class: type) -> bool:
        """
        移除指定类型的checker

        Args:
            checker_class: checker类

        Returns:
            是否成功移除
        """
        for i, checker in enumerate(self.checkers):
            if isinstance(checker, checker_class):
                self.checkers.pop(i)
                return True
        return False

    def clear_checkers(self):
        """清空所有checker"""
        self.checkers = []
