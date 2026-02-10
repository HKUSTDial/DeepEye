"""Direct Schema Linker - Directly link questions to schema elements using LLM."""

import logging
import re
from typing import Any, Dict, List, Optional, Tuple

from langchain_core.language_models import BaseChatModel

from deepeye.datasource.datasource import DatabaseMetadata
from deepeye.agents.nl2sql.schema_linker.base import BaseSchemaLinker
from deepeye.agents.nl2sql.schema_linker.prompt import DIRECT_LINKING_PROMPT
from deepeye.agents.nl2sql.utils.llm_extractor import LLMExtractor
from deepeye.agents.nl2sql.utils.schema_utils import (
    get_database_schema_profile,
    map_lower_table_name_to_original,
    map_lower_column_name_to_original,
)

logger = logging.getLogger(__name__)


class DirectSchemaLinker(BaseSchemaLinker):
    """
    Direct schema linker that uses LLM to directly identify relevant tables and columns.

    This linker prompts the LLM with the database schema and question,
    asking it to identify which tables and columns are needed.
    """

    def __init__(self, fix_end_token: bool = True):
        """
        Initialize the direct schema linker.

        Args:
            fix_end_token: Whether to fix missing end tokens in LLM responses
        """
        self.fix_end_token = fix_end_token
        self.extractor = LLMExtractor()

    async def link(
            self,
            question: str,
            metadata: DatabaseMetadata,
            llm: BaseChatModel,
            evidence: str = "",
            sampling_budget: int = 1,
            **kwargs
    ) -> Tuple[Dict[str, List[str]], Dict[str, int]]:
        """
        Link question to schema using direct LLM prompting.

        Args:
            question: The natural language question
            metadata: Database metadata object
            llm: Language model to use
            evidence: Optional hint/evidence text
            sampling_budget: Number of samples to generate

        Returns:
            Tuple of linked tables/columns dict and token usage dict
        """
        if sampling_budget == 0:
            return {}, {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

        # Generate schema profile
        database_schema_profile = get_database_schema_profile(metadata)

        # Format prompt
        prompt = DIRECT_LINKING_PROMPT.format(
            DATABASE_SCHEMA=database_schema_profile,
            QUESTION=question,
            HINT=evidence or "No additional hints provided."
        ).strip()

        # Extract results
        all_selections, total_token_usage = await self.extractor.extract_with_retry(
            llm=llm,
            messages=[{"role": "user", "content": prompt}],
            rule_parser=self._parse_llm_response,
            parser_kwargs={"metadata": metadata},
            fix_end_token=self.fix_end_token,
            end_token="</r>",
            n=sampling_budget
        )

        # Merge results from multiple samples
        merged_result = self._merge_results(all_selections)

        return merged_result, total_token_usage

    def _parse_llm_response(
            self,
            response: str,
            metadata: DatabaseMetadata
    ) -> Optional[Dict[str, List[str]]]:
        """
        Parse the LLM response to extract linked tables and columns.

        Args:
            response: Raw LLM response text
            metadata: Database metadata for validation

        Returns:
            Dict mapping table names to column names, or None if parsing fails
        """
        try:
            # Extract <r> tag content (result)
            answer_match = re.search(r"<r>(.*?)</r>", response, re.DOTALL)
            if not answer_match:
                # Try alternative tag name
                answer_match = re.search(r"<result>(.*?)</result>", response, re.DOTALL)

            if not answer_match:
                logger.warning("No result tag found in LLM response")
                logger.debug(f"Response content: {response}")
                return None

            answer_content = answer_match.group(1).strip()
            result = {}

            # Extract table elements
            table_matches = re.findall(
                r'<table\s+table_name="([^"]+)"[^>]*>(.*?)</table>',
                answer_content,
                re.DOTALL
            )

            for table_name, table_content in table_matches:
                # Map to original table name
                original_table_name = map_lower_table_name_to_original(
                    table_name.lower(), metadata
                )
                if original_table_name is None:
                    logger.debug(f"Table not found in schema: {table_name}")
                    continue

                result[original_table_name] = []

                # Extract column elements
                column_matches = re.findall(
                    r'<column\s+column_name="([^"]+)"[^>]*/?>',
                    table_content
                )

                for column_name in column_matches:
                    # Map to original column name
                    original_column_name = map_lower_column_name_to_original(
                        original_table_name,
                        column_name.lower(),
                        metadata
                    )
                    if original_column_name is None:
                        logger.debug(f"Column not found: {column_name} in table {original_table_name}")
                        continue
                    result[original_table_name].append(original_column_name)

            if result:
                logger.debug(f"Successfully parsed selection: {len(result)} tables selected")
                return result
            else:
                logger.warning("No valid table-column selections found")
                return None

        except Exception as e:
            logger.warning(f"Error parsing LLM response: {e}")
            logger.debug(f"Response content: {response}")
            return None

    def _merge_results(
            self,
            results: List[Optional[Dict[str, List[str]]]]
    ) -> Dict[str, List[str]]:
        """
        Merge multiple linking results into one.

        Args:
            results: List of linking results from multiple samples

        Returns:
            Merged result dict
        """
        from deepeye.agents.nl2sql.utils.schema_utils import merge_schema_linking_results
        return merge_schema_linking_results(results)