"""Small retrieval diagnostic and optional two-call live planning smoke check.

Run inside backend-api with /app/.venv/bin/python /app/project/scripts/evaluate_analysis_knowledge.py.
No business data or database records are used. Live mode uses the configured model.
"""

import argparse
import asyncio
import json
from pathlib import Path

from app.knowledge.retrieval import retrieve_knowledge

CASES = [
    ("为什么广告点击次数增加，点击率反而降低？", "C02"),
    ("Why did CTR fall when impressions grew?", "C02"),
    ("实验组的分组人数偏少，排查从哪里开始？", "C01"),
    ("We see sample ratio mismatch after bot filtering.", "C01"),
    ("客户端升级后上报事件变多，是真的活跃增长吗？", "C03"),
    ("Client telemetry improved after the release.", "C03"),
    ("每个分群都上涨，但总体没有变化，怎么解释？", "C04"),
    ("实验结果不显著，是不是两组一样？", "C05"),
    ("画一个注册、下单、支付转化漏斗。", "M01"),
    ("How should we define the conversion funnel?", "M01"),
    ("统计新用户七日留存时，如何处理观察不足？", "M02"),
    ("Define retention by cohort and return events.", "M02"),
    ("你好，请介绍一下你自己。", None),
    ("把各城市销售额求和。", None),
    ("Explain abstract syntax trees.", None),
    ("这个指标突然掉了，为什么？", None),
]


async def live_smoke():
    from app.agent.prompts import build_supervisor_prompt
    from app.tasks.agent_tasks import _create_model
    from langchain_core.messages import HumanMessage, SystemMessage

    question = (
        "只讨论分析方法，不执行工作流：某内容模块点击率下滑，但点击总量上涨，"
        "应该怎样制定排查计划？说明需要哪些数据、不能直接下什么结论。"
        "如果本轮提供了参考案例，请给出来源链接；没有则不要编造。"
    )
    model = _create_model()
    model.streaming = False
    model.max_retries = 0
    outputs = []
    for enabled in (False, True):
        selection = retrieve_knowledge(question, enabled=enabled)
        prompt = build_supervisor_prompt(knowledge_context=selection.prompt_context()).format(
            datasources_context="No data sources selected. This is a methodology question."
        )
        response = await asyncio.wait_for(
            model.bind(max_tokens=1800).ainvoke([SystemMessage(content=prompt), HumanMessage(content=question)]),
            timeout=90,
        )
        outputs.append({
            "knowledge_enabled": enabled,
            "retrieved_ids": [m.card.id for m in selection.matches],
            "catalog_version": selection.catalog_version,
            "model": model.model_name,
            "temperature": model.temperature,
            "finish_reason": response.response_metadata.get("finish_reason"),
            "usage": response.usage_metadata,
            "response": response.content,
        })
    return outputs


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--live", action="store_true", help="Make exactly two bounded configured-model calls")
    args = parser.parse_args()
    results = []
    for question, expected in CASES:
        selection = retrieve_knowledge(question)
        ids = [m.card.id for m in selection.matches]
        results.append({
            "question": question, "expected": expected, "retrieved": ids,
            "passed": expected in ids if expected else not ids,
            "prompt_chars": len(selection.prompt_context()),
        })
    report = {
        "scope": "Small development diagnostic; not an independent held-out benchmark or enterprise accuracy estimate.",
        "catalog_version": retrieve_knowledge("CTR").catalog_version,
        "passed": sum(row["passed"] for row in results), "total": len(results), "retrieval": results,
    }
    if args.live:
        report["live_planning_smoke"] = asyncio.run(live_smoke())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"passed": report["passed"], "total": report["total"], "output": str(args.output)}))


if __name__ == "__main__":
    main()
