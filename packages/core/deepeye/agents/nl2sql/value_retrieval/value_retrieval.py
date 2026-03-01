"""
Value Retrieval - 基于字符串相似度的值检索

使用编辑距离、模糊匹配等方法从数据库中检索与问题相关的值
"""

import logging
import re
import json
from typing import List, Dict, Any, Optional, Tuple
from collections import defaultdict
from difflib import SequenceMatcher

from langchain_core.language_models import BaseChatModel

from deepeye.datasource.datasource import DatabaseMetadata
from deepeye.agents.nl2sql.utils.llm_extractor import LLMExtractor
from deepeye.agents.nl2sql.utils.db_utils import execute_sql

logger = logging.getLogger(__name__)


KEYWORDS_EXTRACTION_PROMPT = """
Objective: Analyze the given question and hint to identify and extract keywords, keyphrases, and named entities.

Instructions:
1. Read the Question Carefully: Understand the primary focus and specific details.
2. Analyze the Hint: Extract any keywords, phrases, or named entities.
3. List Keyphrases and Entities: Combine findings into a Python list.

Example:
Question: What is the annual revenue of Acme Corp in the United States for 2022?
Hint: Focus on financial reports and U.S. market performance for the fiscal year 2022.

<r>
["annual revenue", "Acme Corp", "United States", "2022", "financial reports", "U.S. market performance", "fiscal year"]
</r>

Task:
Question: {QUESTION}

Output only the XML format:
<r>
[your_keywords_python_list]
</r>
"""


def levenshtein_distance(s1: str, s2: str) -> int:
    """计算两个字符串的编辑距离（Levenshtein Distance）"""
    if len(s1) < len(s2):
        return levenshtein_distance(s2, s1)

    if len(s2) == 0:
        return len(s1)

    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row

    return previous_row[-1]


def normalized_levenshtein(s1: str, s2: str) -> float:
    """
    归一化的编辑距离，返回0-1之间的相似度
    1表示完全相同，0表示完全不同
    """
    if not s1 and not s2:
        return 1.0
    if not s1 or not s2:
        return 0.0

    distance = levenshtein_distance(s1.lower(), s2.lower())
    max_len = max(len(s1), len(s2))
    return 1 - (distance / max_len)


def sequence_similarity(s1: str, s2: str) -> float:
    """
    使用SequenceMatcher计算字符串相似度
    返回0-1之间的值，1表示完全相同
    """
    return SequenceMatcher(None, s1.lower(), s2.lower()).ratio()


def combined_similarity(s1: str, s2: str) -> float:
    """
    综合相似度：结合编辑距离和序列匹配
    """
    lev_sim = normalized_levenshtein(s1, s2)
    seq_sim = sequence_similarity(s1, s2)
    # 取两者的加权平均
    return 0.5 * lev_sim + 0.5 * seq_sim


def fuzzy_contains(keyword: str, value: str, threshold: float = 0.7) -> Tuple[bool, float]:
    """
    模糊包含检测：检查keyword是否模糊匹配value的某部分

    Returns:
        (是否匹配, 相似度分数)
    """
    keyword = keyword.lower().strip()
    value = value.lower().strip()

    # 精确包含
    if keyword in value or value in keyword:
        return True, 1.0

    # 计算整体相似度
    overall_sim = combined_similarity(keyword, value)
    if overall_sim >= threshold:
        return True, overall_sim

    # 对于较长的value，检查是否包含keyword的子串
    if len(value) > len(keyword):
        # 滑动窗口匹配
        window_size = len(keyword)
        best_sim = 0.0
        for i in range(len(value) - window_size + 1):
            window = value[i:i + window_size]
            sim = combined_similarity(keyword, window)
            best_sim = max(best_sim, sim)

        if best_sim >= threshold:
            return True, best_sim

    return False, overall_sim


class ValueRetriever:
    """
    值检索器：基于字符串相似度从数据库元数据中检索相关值
    """

    def __init__(
            self,
            n_results: int = 10,
            similarity_threshold: float = 0.6,
            db_sample_limit: int = 200,
    ):
        """
        初始化值检索器

        Args:
            n_results: 每列检索的最大结果数量
            similarity_threshold: 相似度阈值，高于此值才认为匹配
            db_sample_limit: 当metadata缺少示例值时，从数据库采样的最大去重值数量
        """
        self.n_results = n_results
        self.similarity_threshold = similarity_threshold
        self.db_sample_limit = max(1, db_sample_limit)
        self.extractor = LLMExtractor()

    async def extract_keywords(
            self,
            question: str,
            llm: BaseChatModel
    ) -> Tuple[List[str], Dict[str, int]]:
        """
        从问题和提示中提取关键词

        Args:
            question: 用户问题
            llm: 语言模型

        Returns:
            关键词列表和token使用统计
        """
        prompt = KEYWORDS_EXTRACTION_PROMPT.format(
            QUESTION=question
        )

        results, token_usage = await self.extractor.extract_with_retry(
            llm=llm,
            messages=[{"role": "user", "content": prompt}],
            rule_parser=self._parse_keywords_response,
            fix_end_token=True,
            end_token="</r>",
            n=1
        )

        if results:
            keywords_list = results[0]
        else:
            logger.warning("Failed to extract keywords, using default splitting strategy")
            keywords_list = self._fallback_keyword_extraction(question)

        # 后处理关键词列表
        processed_keywords = self._process_keywords(keywords_list)

        return processed_keywords, token_usage

    def _fallback_keyword_extraction(self, question: str) -> List[str]:
        """
        关键词提取的回退策略：简单分词
        """
        # 合并问题和证据
        text = f"{question}"

        # 移除标点符号
        text = re.sub(r'[^\w\s]', ' ', text)

        # 分词并过滤短词
        words = [w.strip() for w in text.split() if len(w.strip()) > 1]

        return words

    def _process_keywords(self, keywords_list: List[str]) -> List[str]:
        """
        处理关键词列表：去重、分词
        """
        processed = set()
        for keyword in keywords_list:
            keyword = keyword.strip()
            if keyword:
                processed.add(keyword)
                # 也添加子词
                sub_words = keyword.split()
                for word in sub_words:
                    if len(word) > 1:
                        processed.add(word)

        return list(processed)

    def _parse_keywords_response(self, response: str) -> Optional[List[str]]:
        """解析LLM返回的关键词"""
        try:
            match = re.search(r"<r>(.*?)</r>", response, re.DOTALL)
            if match:
                raw_list = match.group(1).strip()
                keywords_list = json.loads(raw_list)
                if isinstance(keywords_list, list):
                    return keywords_list
            return None
        except Exception as e:
            logger.debug(f"Error parsing keywords: {e}")
            return None

    def retrieve_values(
            self,
            keywords: List[str],
            metadata: DatabaseMetadata,
            database_path: Optional[str] = None,
    ) -> Dict[str, Dict[str, List[Dict[str, Any]]]]:
        """
        基于字符串相似度从数据库元数据中检索相关值

        Args:
            keywords: 关键词列表
            metadata: 数据库元数据（包含示例值和枚举值）
            database_path: 数据库路径或SQLAlchemy URL。仅在metadata缺少候选值时使用

        Returns:
            检索结果字典 {table_name: {column_name: [{value, similarity}]}}
        """
        if not keywords:
            return {}

        retrieved_values = defaultdict(dict)

        for table in metadata.tables:
            for column in table.columns:
                # 先用metadata内的 examples/enums；没有候选值时再尝试在线采样数据库。
                candidate_values = self._collect_candidate_values(
                    table_name=table.name,
                    column_name=column.name,
                    column_type=column.type,
                    metadata_examples=column.examples,
                    metadata_enums=column.enums,
                    database_path=database_path,
                )

                if not candidate_values:
                    continue

                # 对每个关键词进行匹配
                matched_values = []
                for value in candidate_values:
                    best_similarity = 0.0
                    for keyword in keywords:
                        is_match, similarity = fuzzy_contains(
                            keyword, value, self.similarity_threshold
                        )
                        if is_match:
                            best_similarity = max(best_similarity, similarity)

                    if best_similarity >= self.similarity_threshold:
                        matched_values.append({
                            "value": value,
                            "similarity": best_similarity,
                            "distance": 1 - best_similarity
                        })

                # 按相似度排序并取top-k
                if matched_values:
                    matched_values.sort(key=lambda x: x["similarity"], reverse=True)
                    retrieved_values[table.name][column.name] = matched_values[:self.n_results]

        return dict(retrieved_values)

    @staticmethod
    def _quote_ident(identifier: str) -> str:
        """ANSI SQL quoting for identifiers."""
        escaped = identifier.replace('"', '""')
        return f'"{escaped}"'

    @staticmethod
    def _is_textual_column(column_type: Optional[str]) -> bool:
        if not column_type:
            return False
        t = str(column_type).upper()
        keywords = ("CHAR", "TEXT", "STRING", "UUID")
        return any(k in t for k in keywords)

    def _collect_candidate_values(
            self,
            table_name: str,
            column_name: str,
            column_type: Optional[str],
            metadata_examples: Optional[List[Any]],
            metadata_enums: Optional[List[Any]],
            database_path: Optional[str],
    ) -> List[str]:
        candidates: List[str] = []
        seen = set()

        if metadata_examples:
            for value in metadata_examples:
                if value is None:
                    continue
                value_str = str(value)
                if value_str not in seen:
                    seen.add(value_str)
                    candidates.append(value_str)

        if metadata_enums:
            for enum in metadata_enums:
                enum_value = enum.value if hasattr(enum, "value") else enum
                if enum_value is None:
                    continue
                value_str = str(enum_value)
                if value_str not in seen:
                    seen.add(value_str)
                    candidates.append(value_str)

        # Metadata无候选值时，按需从真实数据库采样，避免value retrieval完全失效。
        if not candidates and database_path and self._is_textual_column(column_type):
            db_candidates = self._fetch_distinct_values_from_db(
                table_name=table_name,
                column_name=column_name,
                database_path=database_path,
            )
            for value_str in db_candidates:
                if value_str not in seen:
                    seen.add(value_str)
                    candidates.append(value_str)

        return candidates

    def _fetch_distinct_values_from_db(
            self,
            table_name: str,
            column_name: str,
            database_path: str,
    ) -> List[str]:
        q_table = self._quote_ident(table_name)
        q_column = self._quote_ident(column_name)
        limit = max(1, min(self.db_sample_limit, 1000))
        sql = (
            f"SELECT DISTINCT {q_column} "
            f"FROM {q_table} "
            f"WHERE {q_column} IS NOT NULL "
            f"LIMIT {limit}"
        )

        result = execute_sql(database_path=database_path, sql=sql)
        if result.result_type not in {"success", "empty_result", "all_null_result"}:
            logger.debug(
                "Live value sampling failed for %s.%s: %s",
                table_name,
                column_name,
                result.error_message,
            )
            return []

        sampled_values: List[str] = []
        for row in result.result_rows or []:
            if not row:
                continue
            value = row[0]
            if value is None:
                continue
            sampled_values.append(str(value))

        return sampled_values

    def retrieve_values_sync(
            self,
            keywords: List[str],
            metadata: DatabaseMetadata
    ) -> Dict[str, Dict[str, List[Dict[str, Any]]]]:
        """
        同步版本的值检索（不需要LLM）
        """
        return self.retrieve_values(keywords, metadata)

    def update_metadata_with_values(
            self,
            metadata: DatabaseMetadata,
            retrieved_values: Dict[str, Dict[str, List[Dict[str, Any]]]]
    ) -> DatabaseMetadata:
        """
        使用检索到的值更新数据库元数据

        Args:
            metadata: 原始数据库元数据
            retrieved_values: 检索到的值

        Returns:
            更新后的数据库元数据（深拷贝，原数据不变）
        """
        from copy import deepcopy

        updated_metadata = deepcopy(metadata)

        for table in updated_metadata.tables:
            if table.name not in retrieved_values:
                continue

            table_values = retrieved_values[table.name]
            for column in table.columns:
                if column.name not in table_values:
                    continue

                # 合并新值和原有示例值
                new_values = [v["value"] for v in table_values[column.name]]
                original_values = column.examples or []

                # 去重并合并
                combined = []
                seen = set()
                for v in new_values + original_values:
                    if v not in seen:
                        combined.append(v)
                        seen.add(v)

                column.examples = combined[:self.n_results]

        return updated_metadata


class SimpleValueMatcher:
    """
    简化版的值匹配器：不需要LLM，直接基于字符串匹配

    适用于简单场景，快速检索
    """

    def __init__(
            self,
            similarity_threshold: float = 0.6,
            n_results: int = 10
    ):
        self.similarity_threshold = similarity_threshold
        self.n_results = n_results

    def match(
            self,
            query: str,
            metadata: DatabaseMetadata
    ) -> Dict[str, Dict[str, List[Dict[str, Any]]]]:
        """
        直接对query进行分词并匹配

        Args:
            query: 查询字符串（问题 + 证据）
            metadata: 数据库元数据

        Returns:
            匹配结果
        """
        # 简单分词
        words = re.sub(r'[^\w\s]', ' ', query).split()
        keywords = [w.strip() for w in words if len(w.strip()) > 1]

        retriever = ValueRetriever(
            n_results=self.n_results,
            similarity_threshold=self.similarity_threshold
        )

        return retriever.retrieve_values(keywords, metadata)


if __name__ == '__main__':
    vr = ValueRetriever()
