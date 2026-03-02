"""
NL2SQL Pipeline - 完整的自然语言转SQL管道

整合了以下模块：
- Value Retrieval: 关键词提取和值检索（基于字符串相似度）
- Schema Linking: 表/列链接（Direct, Value两种方法）
- SQL Generation: SQL生成（DC, ICL, Skeleton三种方法）
- SQL Revision: SQL修正（多种checker）
- SQL Selection: SQL选择（成对比较投票）
"""

import logging
from typing import Any, Dict, List, Optional, Tuple
from copy import deepcopy

from langchain_core.language_models import BaseChatModel

from deepeye.datasource.datasource import DatabaseMetadata

# Schema Linkers
from deepeye.agents.nl2sql.schema_linker.direct_linker import DirectSchemaLinker
from deepeye.agents.nl2sql.schema_linker.value_linker import ValueLinker

# SQL Generators
from deepeye.agents.nl2sql.sql_generation.dc_generation import DCGenerator
from deepeye.agents.nl2sql.sql_generation.skeleton_generation import SkeletonGenerator

# SQL Revision
from deepeye.agents.nl2sql.sql_revision.reviser import SQLReviser

# SQL Selection
from deepeye.agents.nl2sql.sql_selection.sql_selection import SQLSelector

# Value Retrieval
from deepeye.agents.nl2sql.value_retrieval.value_retrieval import ValueRetriever, SimpleValueMatcher

# Utils
from deepeye.agents.nl2sql.utils.schema_utils import (
    get_database_schema_profile,
    merge_schema_linking_results,
    filter_used_database_schema,
)

logger = logging.getLogger(__name__)


class NL2SQLPipelineConfig:
    """NL2SQL Pipeline配置"""

    def __init__(
            self,
            # Value Retrieval
            value_retrieval_n_results: int = 10,
            value_similarity_threshold: float = 0.6,
            value_retrieval_use_live_db: bool = True,
            value_retrieval_db_sample_limit: int = 200,
            # Schema Linking
            direct_linking_budget: int = 1,
            reversed_linking_budget: int = 1,
            value_distance_threshold: float = 0.3,
            # SQL Generation
            dc_generation_budget: int = 2,
            icl_generation_budget: int = 2,
            skeleton_generation_budget: int = 2,
            # SQL Revision
            revision_enabled: bool = True,
            # SQL Selection
            selection_top_k: int = 5,
            selection_shortcut_threshold: float = 0.6,
            selection_evaluator_budget: int = 3,
            # General
            fix_end_token: bool = True,
    ):
        # Value Retrieval
        self.value_retrieval_n_results = value_retrieval_n_results
        self.value_similarity_threshold = value_similarity_threshold
        self.value_retrieval_use_live_db = value_retrieval_use_live_db
        self.value_retrieval_db_sample_limit = value_retrieval_db_sample_limit
        # Schema Linking
        self.direct_linking_budget = direct_linking_budget
        self.reversed_linking_budget = reversed_linking_budget
        self.value_distance_threshold = value_distance_threshold
        # SQL Generation
        self.dc_generation_budget = dc_generation_budget
        self.icl_generation_budget = icl_generation_budget
        self.skeleton_generation_budget = skeleton_generation_budget
        # SQL Revision
        self.revision_enabled = revision_enabled
        # SQL Selection
        self.selection_top_k = selection_top_k
        self.selection_shortcut_threshold = selection_shortcut_threshold
        self.selection_evaluator_budget = selection_evaluator_budget
        # General
        self.fix_end_token = fix_end_token


class NL2SQLPipeline:
    """
    完整的NL2SQL Pipeline

    流程：
    1. Value Retrieval: 提取关键词并基于字符串相似度检索相关值
    2. Schema Linking: 链接相关的表和列
    3. SQL Generation: 使用多种方法生成SQL候选
    4. SQL Revision: 修正SQL中的常见问题
    5. SQL Selection: 选择最佳SQL
    """

    def __init__(
            self,
            llm: BaseChatModel,
            db_metadata: DatabaseMetadata,
            database_path: str,
            config: NL2SQLPipelineConfig = None,
    ):
        """
        初始化NL2SQL Pipeline

        Args:
            llm: LangChain语言模型
            db_metadata: 数据库元数据
            database_path: 数据库文件路径（用于执行SQL验证）
            config: Pipeline配置
        """
        self.llm = llm
        self.db_metadata = db_metadata
        self.database_path = database_path
        self.config = config or NL2SQLPipelineConfig()

        # 初始化各模块
        self._init_modules()

    def _init_modules(self):
        """初始化各个模块"""
        # Value Retrieval（基于字符串相似度）
        self.value_retriever = ValueRetriever(
            n_results=self.config.value_retrieval_n_results,
            similarity_threshold=self.config.value_similarity_threshold,
            db_sample_limit=self.config.value_retrieval_db_sample_limit,
        )

        # Schema Linkers
        self.direct_linker = DirectSchemaLinker(
            fix_end_token=self.config.fix_end_token
        )
        self.value_linker = ValueLinker(
            value_distance_threshold=self.config.value_distance_threshold
        )

        # SQL Generators
        self.dc_generator = DCGenerator(
            fix_end_token=self.config.fix_end_token
        )

        self.skeleton_generator = SkeletonGenerator(
            fix_end_token=self.config.fix_end_token
        )

        # SQL Revision
        self.sql_reviser = SQLReviser(
            fix_end_token=self.config.fix_end_token
        )

        # SQL Selection
        self.sql_selector = SQLSelector(
            filter_top_k=self.config.selection_top_k,
            shortcut_threshold=self.config.selection_shortcut_threshold,
            evaluator_budget=self.config.selection_evaluator_budget,
            fix_end_token=self.config.fix_end_token,
        )

    async def run(
            self,
            question: str,
            evidence: str = "",
            few_shot_examples: List[Dict[str, Any]] = None,
            skip_value_retrieval: bool = False,
            skip_schema_linking: bool = False,
            skip_revision: bool = False,
            skip_selection: bool = False,
    ) -> Dict[str, Any]:
        """
        运行完整的NL2SQL Pipeline

        Args:
            question: 用户问题
            evidence: 提示/证据信息
            few_shot_examples: ICL生成器的few-shot示例
            skip_value_retrieval: 跳过值检索
            skip_schema_linking: 跳过schema linking
            skip_revision: 跳过SQL修正
            skip_selection: 跳过SQL选择

        Returns:
            包含所有中间结果和最终SQL的字典
        """
        result = {
            "question": question,
            "evidence": evidence,
            "total_tokens": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
        }

        # 当前使用的元数据（会在各阶段更新）
        current_metadata = deepcopy(self.db_metadata)

        # ========== 1. Value Retrieval ==========
        if not skip_value_retrieval:
            logger.info("Running Value Retrieval...")
            vr_result = await self._run_value_retrieval(
                question, evidence, current_metadata
            )
            result["value_retrieval"] = vr_result
            self._accumulate_tokens(result, vr_result.get("tokens", {}))

            if vr_result.get("updated_metadata"):
                current_metadata = vr_result["updated_metadata"]
                result["retrieved_values"] = vr_result.get("retrieved_values", {})

        # ========== 2. Schema Linking ==========
        if not skip_schema_linking:
            logger.info("Running Schema Linking...")
            sl_result = await self._run_schema_linking(
                question, evidence, current_metadata,
                result.get("retrieved_values", {})
            )
            result["schema_linking"] = sl_result
            self._accumulate_tokens(result, sl_result.get("tokens", {}))

            if sl_result.get("filtered_metadata"):
                current_metadata = sl_result["filtered_metadata"]

        result["final_metadata"] = current_metadata

        # ========== 3. SQL Generation ==========
        logger.info("Running SQL Generation...")
        gen_result = await self._run_sql_generation(
            question, evidence, current_metadata, few_shot_examples
        )
        result["sql_generation"] = gen_result
        self._accumulate_tokens(result, gen_result.get("tokens", {}))

        sql_candidates = gen_result.get("candidates", [])

        if not sql_candidates:
            logger.warning("No SQL candidates generated")
            result["final_sql"] = ""
            return result

        # ========== 4. SQL Revision ==========
        if not skip_revision and self.config.revision_enabled:
            logger.info("Running SQL Revision...")
            rev_result = await self._run_sql_revision(
                sql_candidates, current_metadata, question, evidence
            )
            result["sql_revision"] = rev_result
            self._accumulate_tokens(result, rev_result.get("tokens", {}))
            sql_candidates = rev_result.get("revised_candidates", sql_candidates)

        # ========== 5. SQL Selection ==========
        if not skip_selection and len(sql_candidates) > 1:
            logger.info("Running SQL Selection...")
            sel_result = await self._run_sql_selection(
                sql_candidates, current_metadata, question, evidence
            )
            result["sql_selection"] = sel_result
            self._accumulate_tokens(result, sel_result.get("tokens", {}))
            result["final_sql"] = sel_result.get("selected_sql", sql_candidates[0])
        else:
            result["final_sql"] = sql_candidates[0] if sql_candidates else ""

        logger.info(f"Pipeline completed. Final SQL: {result['final_sql'][:100]}...")
        return result

    async def _run_value_retrieval(
            self,
            question: str,
            evidence: str,
            metadata: DatabaseMetadata
    ) -> Dict[str, Any]:
        """运行值检索阶段（基于字符串相似度）"""
        result = {"tokens": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}}

        try:
            # 提取关键词（使用LLM）
            keywords, kw_tokens = await self.value_retriever.extract_keywords(
                question, self.llm
            )
            result["keywords"] = keywords
            self._accumulate_tokens(result, kw_tokens)

            # 基于字符串相似度检索值（不使用向量数据库）
            retrieved_values = self.value_retriever.retrieve_values(
                keywords,
                metadata,
                database_path=self.database_path if self.config.value_retrieval_use_live_db else None,
            )
            result["retrieved_values"] = retrieved_values

            # 更新元数据
            updated_metadata = self.value_retriever.update_metadata_with_values(
                metadata, retrieved_values
            )
            result["updated_metadata"] = updated_metadata

        except Exception as e:
            logger.error(f"Value retrieval failed: {e}")
            result["error"] = str(e)

        return result

    async def _run_schema_linking(
            self,
            question: str,
            evidence: str,
            metadata: DatabaseMetadata,
            retrieved_values: Dict = None
    ) -> Dict[str, Any]:
        """运行Schema Linking阶段"""
        result = {"tokens": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}}

        linking_results = []

        try:
            # Direct Linking
            if self.config.direct_linking_budget > 0:
                direct_result, direct_tokens = await self.direct_linker.link(
                    question, metadata, self.llm, evidence,
                    sampling_budget=self.config.direct_linking_budget
                )
                result["direct_linking"] = direct_result
                self._accumulate_tokens(result, direct_tokens)
                if direct_result:
                    linking_results.append(direct_result)

            # Value Linking（基于检索到的值）
            if retrieved_values:
                value_result, value_tokens = await self.value_linker.link(
                    question, metadata, self.llm,
                    retrieved_values=retrieved_values
                )
                result["value_linking"] = value_result
                self._accumulate_tokens(result, value_tokens)
                if value_result:
                    linking_results.append(value_result)

            # 合并结果
            merged = merge_schema_linking_results(linking_results)
            result["merged_linking"] = merged

            # 过滤元数据
            if merged:
                filtered = filter_used_database_schema(metadata, merged)
                result["filtered_metadata"] = filtered

        except Exception as e:
            logger.error(f"Schema linking failed: {e}")
            result["error"] = str(e)

        return result

    async def _run_sql_generation(
            self,
            question: str,
            evidence: str,
            metadata: DatabaseMetadata,
            few_shot_examples: List[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """运行SQL生成阶段"""
        result = {
            "tokens": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
            "candidates": []
        }

        try:
            # DC Generation
            if self.config.dc_generation_budget > 0:
                dc_sqls, dc_tokens = await self.dc_generator.generate(
                    question, metadata, self.llm,
                    sampling_budget=self.config.dc_generation_budget
                )
                result["dc_candidates"] = dc_sqls
                result["candidates"].extend(dc_sqls)
                self._accumulate_tokens(result, dc_tokens)

            # Skeleton Generation
            if self.config.skeleton_generation_budget > 0:
                skel_sqls, skel_tokens = await self.skeleton_generator.generate(
                    question, metadata, self.llm,
                    sampling_budget=self.config.skeleton_generation_budget
                )
                result["skeleton_candidates"] = skel_sqls
                result["candidates"].extend(skel_sqls)
                self._accumulate_tokens(result, skel_tokens)

        except Exception as e:
            logger.error(f"SQL generation failed: {e}")
            result["error"] = str(e)

        return result

    async def _run_sql_revision(
            self,
            sql_candidates: List[str],
            metadata: DatabaseMetadata,
            question: str,
            evidence: str
    ) -> Dict[str, Any]:
        """运行SQL修正阶段"""
        result = {
            "tokens": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
            "revised_candidates": []
        }

        try:
            for sql in sql_candidates:
                revised_sql, tokens = await self.sql_reviser.revise(
                    sql, metadata, self.llm,
                    self.database_path, question, evidence
                )
                result["revised_candidates"].append(revised_sql)
                self._accumulate_tokens(result, tokens)

        except Exception as e:
            logger.error(f"SQL revision failed: {e}")
            result["error"] = str(e)
            result["revised_candidates"] = sql_candidates

        return result

    async def _run_sql_selection(
            self,
            sql_candidates: List[str],
            metadata: DatabaseMetadata,
            question: str,
            evidence: str
    ) -> Dict[str, Any]:
        """运行SQL选择阶段"""
        result = {"tokens": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}}

        try:
            selected_sql, tokens = await self.sql_selector.select(
                sql_candidates, metadata, self.llm,
                self.database_path, question, evidence
            )
            result["selected_sql"] = selected_sql
            self._accumulate_tokens(result, tokens)

        except Exception as e:
            logger.error(f"SQL selection failed: {e}")
            result["error"] = str(e)
            result["selected_sql"] = sql_candidates[0] if sql_candidates else ""

        return result

    def _accumulate_tokens(self, result: Dict, tokens: Dict[str, int]):
        """累加token统计"""
        bucket_key = "total_tokens" if "total_tokens" in result else "tokens"
        if bucket_key not in result or not isinstance(result[bucket_key], dict):
            result[bucket_key] = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        for key in ["prompt_tokens", "completion_tokens", "total_tokens"]:
            if key in tokens:
                result[bucket_key][key] = result[bucket_key].get(key, 0) + tokens[key]

    async def generate_sql(self, question: str, evidence: str = "") -> str:
        """
        直接生成SQL

        Args:
            question: 用户问题
            evidence: 提示信息

        Returns:
            生成的SQL语句
        """
        result = await self.run(question, evidence)
        return result.get("final_sql", "")


async def nl2sql(
        question: str,
        llm: BaseChatModel,
        db_metadata: DatabaseMetadata,
        database_path: str,
        evidence: str = "",
        **kwargs
) -> str:
    """
    便捷函数：一行代码完成NL2SQL转换

    Args:
        question: 用户问题
        llm: LangChain语言模型
        db_metadata: 数据库元数据
        database_path: 数据库路径
        evidence: 提示信息
        **kwargs: 其他配置参数

    Returns:
        生成的SQL语句
    """
    config = NL2SQLPipelineConfig(**kwargs) if kwargs else None
    pipeline = NL2SQLPipeline(llm, db_metadata, database_path, config)
    return await pipeline.generate_sql(question, evidence)
