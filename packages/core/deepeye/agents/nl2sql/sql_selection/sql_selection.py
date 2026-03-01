"""
SQL Selection - SQL选择模块

通过成对比较和投票机制选择最佳SQL
"""

import logging
import re
from typing import Dict, List, Tuple, Optional, Any
from collections import Counter

from langchain_core.language_models import BaseChatModel

from deepeye.datasource.datasource import DatabaseMetadata
from deepeye.agents.nl2sql.utils.llm_extractor import LLMExtractor
from deepeye.agents.nl2sql.utils.schema_utils import get_database_schema_profile
from deepeye.agents.nl2sql.utils.db_utils import execute_sql

logger = logging.getLogger(__name__)


BR_PAIR_SELECTION_PROMPT = """
# Task:
Compare two SQL candidates and select the better one.

# Important Context:
- SQL Candidate A has higher confidence
- Only choose B if there is clear evidence it is superior

# Database Schema:
{DATABASE_SCHEMA}

# Question:
{QUESTION}

# Hint:
{HINT}

SQL Candidate A:
{QUERY_A}

Execution Result A:
{RESULT_A}

SQL Candidate B:
{QUERY_B}

Execution Result B:
{RESULT_B}

# Output Format:
<r>
    A or B (just the letter)
</r>
"""


class SQLSelector:
    """
    SQL选择器：通过成对比较选择最佳SQL
    """

    def __init__(
            self,
            filter_top_k: int = 5,
            shortcut_threshold: float = 0.6,
            evaluator_budget: int = 3,
            fix_end_token: bool = True
    ):
        """
        初始化SQL选择器

        Args:
            filter_top_k: 筛选的top-k SQL数量
            shortcut_threshold: 快捷选择阈值（一致性分数高于此值直接选择）
            evaluator_budget: 每对比较的投票次数
            fix_end_token: 是否修复结束标签
        """
        self.filter_top_k = filter_top_k
        self.shortcut_threshold = shortcut_threshold
        self.evaluator_budget = evaluator_budget
        self.fix_end_token = fix_end_token
        self.extractor = LLMExtractor()

    async def select(
            self,
            sql_candidates: List[str],
            metadata: DatabaseMetadata,
            llm: BaseChatModel,
            database_path: str,
            question: str = "",
            evidence: str = ""
    ) -> Tuple[str, Dict[str, int]]:
        """
        从SQL候选中选择最佳SQL

        Args:
            sql_candidates: SQL候选列表
            metadata: 数据库元数据
            llm: 语言模型
            database_path: 数据库路径
            question: 用户问题
            evidence: 提示信息

        Returns:
            最佳SQL和token使用统计
        """
        total_tokens = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

        if not sql_candidates:
            return "", total_tokens

        if len(sql_candidates) == 1:
            return sql_candidates[0], total_tokens

        # 获取top-k候选
        top_k_candidates = self._get_top_k_candidates(sql_candidates, database_path)

        if not top_k_candidates:
            logger.warning("No valid SQL candidates, returning first candidate")
            return sql_candidates[0], total_tokens

        if len(top_k_candidates) == 1:
            return top_k_candidates[0][0], total_tokens

        # 快捷选择：如果top-1的一致性分数足够高
        if top_k_candidates[0][2] >= self.shortcut_threshold:
            logger.info(f"Shortcut selection: top-1 consistency score = {top_k_candidates[0][2]}")
            return top_k_candidates[0][0], total_tokens

        # 成对比较
        selected_sql, tokens = await self._pairwise_selection(
            top_k_candidates, metadata, llm, question, evidence
        )
        for key in total_tokens:
            total_tokens[key] += tokens.get(key, 0)

        return selected_sql, total_tokens

    def _get_top_k_candidates(
            self,
            sql_candidates: List[str],
            database_path: str
    ) -> List[Tuple[str, str, float]]:
        """
        获取top-k有效SQL候选

        Returns:
            [(sql, result_str, consistency_score), ...]
        """
        valid_candidates = []
        sql_to_result_str = {}

        for sql in sql_candidates:
            result = execute_sql(database_path, sql)
            if result.result_rows is not None and len(result.result_rows) > 0:
                valid_candidates.append((sql, frozenset(result.result_rows)))
                sql_to_result_str[sql] = result.result_table_str

        if not valid_candidates:
            # 退化到有结果但可能为空的候选
            for sql in sql_candidates:
                result = execute_sql(database_path, sql)
                if result.result_rows is not None:
                    valid_candidates.append((sql, frozenset(result.result_rows)))
                    sql_to_result_str[sql] = result.result_table_str or "Empty result"

        if not valid_candidates:
            return []

        # 计算一致性分数
        counter = Counter(r for _, r in valid_candidates)

        # 去重并排序
        seen_results = set()
        deduplicated = []
        for sql, result_set in valid_candidates:
            if result_set not in seen_results:
                consistency = counter[result_set] / len(valid_candidates)
                deduplicated.append((sql, sql_to_result_str.get(sql, ""), consistency))
                seen_results.add(result_set)

        # 按一致性分数排序
        return sorted(deduplicated, key=lambda x: x[2], reverse=True)[:self.filter_top_k]

    async def _pairwise_selection(
            self,
            candidates: List[Tuple[str, str, float]],
            metadata: DatabaseMetadata,
            llm: BaseChatModel,
            question: str,
            evidence: str
    ) -> Tuple[str, Dict[str, int]]:
        """
        成对比较选择最佳SQL

        Args:
            candidates: [(sql, result_str, consistency_score), ...]
            metadata: 数据库元数据
            llm: 语言模型
            question: 用户问题
            evidence: 提示信息

        Returns:
            最佳SQL和token使用统计
        """
        total_tokens = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        n = len(candidates)

        # 初始化胜利矩阵 [candidate_i][candidate_j][vote_k]
        win_matrix: List[List[List[float]]] = [
            [[0.0 for _ in range(self.evaluator_budget)] for _ in range(n)]
            for _ in range(n)
        ]

        # 生成所有对
        pairs = []
        for i in range(n):
            for j in range(i + 1, n):
                pairs.append((i, j))

        # 执行成对比较
        database_schema_profile = get_database_schema_profile(metadata)

        for i, j in pairs:
            sql_a, result_a, _ = candidates[i]
            sql_b, result_b, _ = candidates[j]

            votes, tokens = await self._compare_pair(
                database_schema_profile, question, evidence,
                sql_a, result_a, sql_b, result_b, llm
            )

            for key in total_tokens:
                total_tokens[key] += tokens.get(key, 0)

            # 更新胜利矩阵
            for k, vote in enumerate(votes):
                if vote == "A":
                    win_matrix[i][j][k] = 1.0
                    win_matrix[j][i][k] = 0.0
                elif vote == "B":
                    win_matrix[j][i][k] = 1.0
                    win_matrix[i][j][k] = 0.0
                else:  # TIE
                    win_matrix[i][j][k] = 0.5
                    win_matrix[j][i][k] = 0.5

        # 计算最终得分
        robust_matrix: List[List[float]] = []
        for i in range(n):
            robust_row = []
            for j in range(n):
                robust_row.append(sum(win_matrix[i][j]) / max(1, self.evaluator_budget))
            robust_matrix.append(robust_row)

        scores = [sum(row) / max(1, n) for row in robust_matrix]

        # 加权一致性分数
        consistency_weights = [c[2] for c in candidates]
        weight_sum = sum(consistency_weights)
        if weight_sum <= 0:
            normalized_weights = [1.0 / n for _ in range(n)]
        else:
            normalized_weights = [w / weight_sum for w in consistency_weights]
        final_scores = [scores[idx] * normalized_weights[idx] for idx in range(n)]

        best_idx = max(range(n), key=lambda idx: final_scores[idx])
        return candidates[best_idx][0], total_tokens

    async def _compare_pair(
            self,
            schema_profile: str,
            question: str,
            evidence: str,
            sql_a: str,
            result_a: str,
            sql_b: str,
            result_b: str,
            llm: BaseChatModel
    ) -> Tuple[List[str], Dict[str, int]]:
        """
        比较一对SQL

        Returns:
            投票列表和token使用统计
        """
        prompt = BR_PAIR_SELECTION_PROMPT.format(
            DATABASE_SCHEMA=schema_profile,
            QUESTION=question,
            HINT=evidence or "No hint provided.",
            QUERY_A=sql_a,
            RESULT_A=result_a,
            QUERY_B=sql_b,
            RESULT_B=result_b
        )

        votes, token_usage = await self.extractor.extract_with_retry(
            llm=llm,
            messages=[{"role": "user", "content": prompt}],
            rule_parser=self._parse_vote,
            fix_end_token=self.fix_end_token,
            end_token="</r>",
            n=self.evaluator_budget
        )

        return votes, token_usage

    def _parse_vote(self, response: str) -> Optional[str]:
        """解析投票结果"""
        try:
            match = re.search(r"<r>(.*?)</r>", response, re.DOTALL)
            if not match:
                return None
            content = match.group(1).strip().upper()
            if content in ["A", "B", "TIE"]:
                return content
            return None
        except Exception:
            return None
