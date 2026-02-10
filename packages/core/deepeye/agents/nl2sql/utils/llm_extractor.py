"""
大模型调用及抽取（2026-02-03 已完成）
"""

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, AIMessage

import logging
from typing import List, Any, Callable, Tuple, Dict, TypeVar, Optional

logger = logging.getLogger(__name__)

T = TypeVar('T')


class LLMExtractor:
    """
    从LLM 的 response里面解析出结构化的数据，并支持大模型的失败调用重试
    """

    def __init__(self, max_retries: int = 3):
        """
        对 LLM Extractor 进行初始化
        """
        self.max_retries = max_retries

    async def extract_with_retry(
            self,
            llm: BaseChatModel,
            messages: List[Dict[str, str]],
            rule_parser: Callable[..., Optional[T]],
            parser_kwargs: Optional[Dict[str, Any]] = None,
            fix_end_token: bool = False,
            end_token: str = "</result>",
            n: int = 1,
            **llm_kwargs
    ) -> Tuple[list, Dict[str, int]]:
        """
        Call LLM and parse responses with retry logic.

        This method will:
        1. Call the LLM to get responses
        2. For each response, try rule-based parsing
        3. Retry up to max_retry times if not enough valid results

        Args:
            llm: The LLM to call for generating responses
            messages: The messages to send to the LLM
            rule_parser: A callable that attempts to parse the response using rules
            parser_kwargs: Additional keyword arguments to pass to the rule_parser
            fix_end_token: Whether to fix missing end tokens
            end_token: The end token to append if missing
            n: Target number of successfully parsed results
            **llm_kwargs: Additional keyword arguments to pass to the LLM

        Returns:
            Tuple of (list of parsed results, total token_usage_dict)
        """
        total_token_usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        all_results = []
        parser_kwargs = parser_kwargs or {}
        retry_count = 0
        max_retry = self.max_retries

        lc_messages = []

        # message -> [{"role": "user", "content": "你是谁？"}, {"role": "assistant", "content": "my name is grok"}]
        # new_messages -> [HumanMessage('hello'), AIMessage('My name is Grok'), ....]

        for msg in messages:
            if msg['role'] == 'user':
                lc_messages.append(HumanMessage(content=msg['content']))
            elif msg['role'] == 'assistant':
                lc_messages.append(AIMessage(content=msg['content']))

        for sample_idx in range(n):
            retry_count = 0

            # 开始重试循环
            while retry_count < self.max_retries:
                try:
                    # 调用LLM
                    response = await llm.ainvoke(lc_messages)
                    response_text = response.content

                    if hasattr(response, 'response_metadata'):
                        metadata = response.response_metadata
                        if 'token_usage' in metadata:
                            usage = metadata['token_usage']
                            total_token_usage["prompt_tokens"] += usage.get("prompt_tokens", 0)
                            total_token_usage["completion_tokens"] += usage.get("completion_tokens", 0)
                            total_token_usage["total_tokens"] += usage.get("total_tokens", 0)

                    if fix_end_token and end_token not in response_text:
                        response_text = response_text + end_token

                    parsed_result = rule_parser(response_text, **parser_kwargs)

                    if parsed_result is not None:
                        all_results.append(parsed_result)
                        break

                    else:
                        logger.warning("响应解析失败")
                        retry_count += 1

                except Exception as e:
                    logger.error(e)
                    retry_count += 1

                if retry_count >= self.max_retries:
                    logger.warning('最大重试次数已达到，即将退出')

        return all_results, total_token_usage

