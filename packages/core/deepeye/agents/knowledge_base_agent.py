from langchain_core.language_models import BaseChatModel
from langgraph.checkpoint.base import BaseCheckpointSaver

from deepeye.agents.react_agent import ReActAgent

KNOWLEDGE_BASE_AGENT_SYSTEM_PROMPT = """You are a Knowledge Base Assistant.
Your job is to answer user questions by querying the knowledge base tables with SQL.

Rules:
1) Always call execute_kb_sql before answering if the question depends on knowledge base content.
2) Use the returned rows as the source of truth; do not fabricate details.
3) If execute_kb_sql returns no rows, say you couldn't find relevant information.
4) Keep the response concise and in the user's language.

SQL requirements:
- Use SELECT only.
- Must include filters with :user_id and :kb_ids.
- Target tables: knowledge_bases, knowledge_base_files, knowledge_base_chunks.

Example template:
SELECT c.content, f.filename, c.chunk_index
FROM knowledge_base_chunks c
JOIN knowledge_base_files f ON f.id = c.file_id
WHERE f.user_id = :user_id
  AND c.kb_id = ANY(:kb_ids)
  AND c.content ILIKE :keyword
ORDER BY c.chunk_index
LIMIT 5
"""


class KnowledgeBaseAgent(ReActAgent):
    """Agent that queries knowledge bases and answers."""

    def __init__(
        self,
        model: BaseChatModel,
        tools: list | None = None,
        checkpointer: BaseCheckpointSaver | None = None,
        system_prompt: str = KNOWLEDGE_BASE_AGENT_SYSTEM_PROMPT,
        max_steps: int = 30,
    ):
        super().__init__(
            model=model,
            tools=tools or [],
            system_prompt=system_prompt,
            checkpointer=checkpointer,
            max_steps=max_steps,
        )
