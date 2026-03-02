"""
SQL Generation Base Class

SQL 生成器的基类
"""
import logging
import re
from typing import List, Dict, Any, Tuple, Optional
from abc import ABC, abstractmethod

from langchain_core.language_models import BaseChatModel

from deepeye.datasource.datasource import DatabaseMetadata


logger = logging.getLogger(__name__)


class BaseSQLGenerator(ABC):

    @abstractmethod
    async def generate(
            self,
            question: str,
            metadata: DatabaseMetadata,
            llm: BaseChatModel,
            sampling_budget: int = 1,
            **kwargs
    ) -> Tuple[List[str], Dict[str, int]]:
        """
        生成SQL查询

        Args:
            question: 问题
            metadata: 数据元数据
            llm: LLM
            sampling_budget: 采样次数

        Returns: ([SELECT * FROM xxx, ...], {tokens 消耗})
        """

        raise NotImplementedError

    def _parse_llm_response(self, response: str) -> Optional[str]:
        """
        解析大模型的响应，从响应中提取出 SQL语句
        """
        try:
            answer_match = re.search(r'<result>(.*?)</result>', response, re.DOTALL)

            if not answer_match:
                logger.error('大模型生成的回复中没有找到 <result> 包裹的内容')
                return None

            answer_content = answer_match.group(1).strip()

            # 去掉可能存在的markdown包裹
            if answer_content.startswith('```sql') and answer_content.endswith('```'):
                answer_content = answer_content[len('```sql'):-len("```")].strip()
            elif answer_content.startswith("```") and answer_content.endswith("```"):
                answer_content = answer_content[3:-3].strip()

            return answer_content

        except Exception as e:
            logger.error(e)
            return None


if __name__ == '__main__':

    text = """
 <result> ```sql 你好，我是一段SQL ``` </result>   
    """

    answer_match = re.search(r'<result>(.*?)</result>', text, re.DOTALL)


