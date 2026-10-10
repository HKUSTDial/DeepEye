"""Publish deterministic retrieval through existing tool-step events and storage."""

import json

from app.knowledge.retrieval import Selection
from app.tasks.callbacks import AgentCallback
from deepeye.utils.logger import logger


async def publish_knowledge_selection(callback: AgentCallback, selection: Selection) -> None:
    if selection.status == "disabled":
        return
    trace = selection.trace()
    trace["notice"] = "检索到的参考资料不代表已采用、已满足数据条件或已执行验证。"
    logger.info(
        "[analysis_knowledge] %s",
        json.dumps(
            {"session_id": callback.session_id, "turn_id": callback.turn_id, **trace},
            ensure_ascii=False,
        ),
    )
    await callback.on_tool_start(
        {"name": "analysis_knowledge"},
        "按当前问题检索互联网分析案例与方法（关键词／标签基线）",
    )
    await callback.on_tool_end(json.dumps(trace, ensure_ascii=False, indent=2))
