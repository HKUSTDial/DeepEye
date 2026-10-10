"""Reproducible three-arm knowledge evaluation, with isolated SQL execution.

Offline by default; --live makes at most 24 model calls (no retries).
Run with PYTHONPATH=packages/backend and configured LLM_* environment variables.
This is a small author-created acceptance suite, not a blinded benchmark.
"""

import argparse
import hashlib
import json
import math
import os
import sqlite3
import time
import urllib.request
from pathlib import Path

from app.knowledge.retrieval import Match, Selection, load_catalog, retrieve_knowledge

CASES = [
    {"id": "A01", "card": "C02", "question": "广告点击从 30 增长至 36，展示从 100 增长到 180。只讨论 CTR 的分析方法，能直接判断改版更差吗？",
     "rubric": ["区分总量与比率", "核对用户均值和总体比率", "不能从观察变化判断因果或收入", "有参考知识时引用实际来源"]},
    {"id": "A02", "card": "M02", "question": "只讨论方法：昨天注册的用户还没有第七天行为，周报把他们算成七日留存失败了，合理吗？",
     "rubric": ["指出观察期未成熟", "澄清精确第7日和滚动留存", "不把观察不足算流失", "有参考知识时引用实际来源"]},
    {"id": "A03", "card": "C06", "question": "只讨论方法：用户级随机 A/B 实验每天看p值，一显著就提前停止，且把每次播放都当独立样本，有什么问题？",
     "rubric": ["识别反复查看与停止偏差", "识别用户内依赖", "不能只建议使用任意序贯检验", "有参考知识时引用实际来源"]},
    {"id": "A04", "card": "C07", "question": "只讨论方法：三个功能实验收益分别为 2%、3%、4%，季度收益相加报 9% 是否可靠？",
     "rubric": ["加总需可比基线和人群", "指出交互或重叠曝光", "组合效果需直接评估或明确假设", "有参考知识时引用实际来源"]},
    {"id": "X01", "card": "C02", "question": "计算各期总点击、总曝光、总体 CTR 与平均用户 CTR，按 period 升序。曝光均为正，每行是一位用户一期的聚合。",
     "setup": "CREATE TABLE metrics(period TEXT,user_id TEXT,clicks INTEGER,impressions INTEGER); INSERT INTO metrics VALUES ('before','u',2,5),('before','v',4,10),('after','u',3,5),('after','v',6,40);",
     "expected": [["after",9,45,.2,.375],["before",6,15,.4,.4]]},
    {"id": "X02", "card": "M01", "question": "计算首次 signup 用户数、转化用户数、转化率。UTC 小时；pay 严格晚于首次 signup 且在24小时内（含24）；去重用户；所有用户观察完整。只返回一行三列。",
     "setup": "CREATE TABLE events(user_id TEXT,event TEXT,hour INTEGER); INSERT INTO events VALUES ('a','signup',10),('a','pay',11),('a','pay',12),('b','signup',10),('b','pay',34),('c','signup',10),('c','pay',10),('d','signup',10),('d','pay',35),('e','pay',9),('e','signup',10),('f','signup',10);",
     "expected": [[6,2,1/3]]},
    {"id": "X03", "card": "M02", "question": "计算精确自然日D7的成熟用户数、留存人数、留存率。signup 已去重为首次注册；UTC 自然日；完整观测到2026-01-10当日结束；回访去重；观察不足者排除。只返回一行三列。",
     "setup": "CREATE TABLE users(user_id TEXT,signup TEXT); CREATE TABLE visits(user_id TEXT,day TEXT); INSERT INTO users VALUES ('a','2026-01-01'),('b','2026-01-02'),('c','2026-01-03'),('d','2026-01-04'),('e','2026-01-08'); INSERT INTO visits VALUES ('a','2026-01-08'),('a','2026-01-08'),('b','2026-01-08'),('d','2026-01-10');",
     "expected": [[3,1,1/3]]},
    {"id": "X04", "card": "C01", "question": "用户级1:1分配已确认。按stage升序报告各阶段总人数和Pearson分配比例卡方统计量。不计算p值、不下效果结论。列顺序stage,total,chi_square。",
     "setup": "CREATE TABLE counts(stage TEXT,arm TEXT,n INTEGER); INSERT INTO counts VALUES ('assigned','control',80),('assigned','treatment',80),('kept','control',72),('kept','treatment',48);",
     "expected": [["assigned",160,0],["kept",120,4.8]]},
]


def readonly_query(setup, query):
    """Untrusted model SQL gets no file/network access and no writes."""
    if not isinstance(query, str) or len(query) > 20000:
        raise ValueError("Invalid query size")
    with sqlite3.connect(":memory:") as db:
        db.executescript(setup)  # Trusted fixture only.
        allowed = {sqlite3.SQLITE_SELECT, sqlite3.SQLITE_READ, sqlite3.SQLITE_FUNCTION, sqlite3.SQLITE_RECURSIVE}
        functions = {"sum", "avg", "count", "min", "max", "nullif", "coalesce", "ifnull", "round", "abs", "date", "datetime", "julianday", "strftime", "cast"}

        def authorize(action, arg1, arg2, *_):
            if action == sqlite3.SQLITE_FUNCTION and (arg2 or "").lower() not in functions:
                return sqlite3.SQLITE_DENY
            return sqlite3.SQLITE_OK if action in allowed else sqlite3.SQLITE_DENY

        db.set_authorizer(authorize)
        deadline = time.monotonic() + 2
        db.set_progress_handler(lambda: int(time.monotonic() > deadline), 1000)
        cursor = db.execute(query)
        rows = cursor.fetchmany(101)
        if len(rows) > 100:
            raise ValueError("Too many result rows")
        return rows


def equal_rows(actual, expected):
    if len(actual) != len(expected):
        return False
    for row, reference in zip(actual, expected, strict=True):
        if len(row) != len(reference):
            return False
        for a, b in zip(row, reference, strict=True):
            if isinstance(b, (int, float)):
                # Six-decimal rate output is acceptable; integer counts stay exact.
                tolerance = 0 if isinstance(b, int) else 5e-7
                if not isinstance(a, (int, float)) or not math.isclose(a, b, rel_tol=0, abs_tol=tolerance):
                    return False
            elif a != b:
                return False
    return True


def model_call(system, question):
    payload = {"model": os.environ["LLM_MODEL"], "temperature": 0,
               "max_tokens": int(os.environ.get("LLM_MAX_TOKENS", "8192")), "messages": [{"role": "system", "content": system}, {"role": "user", "content": question}]}
    request = urllib.request.Request(os.environ["LLM_BASE_URL"].rstrip("/") + "/chat/completions",
                                     data=json.dumps(payload).encode(), headers={"Content-Type": "application/json", "Authorization": "Bearer " + os.environ["LLM_API_KEY"]})
    with urllib.request.urlopen(request, timeout=90) as response:
        result = json.load(response)
    choice = result["choices"][0]
    return choice["message"]["content"], choice.get("finish_reason"), result.get("usage")


def run(output, live=False):
    cards, version = load_catalog()
    catalog = {card.id: card for card in cards}
    report = {"scope": "Small author-created acceptance set; one call per arm; not an independent statistical benchmark or full application E2E.",
              "catalog_version": version, "cases_sha256": hashlib.sha256(json.dumps(CASES, sort_keys=True).encode()).hexdigest(),
              "model": os.environ.get("LLM_MODEL") if live else None, "temperature": 0,
              "max_tokens": int(os.environ.get("LLM_MAX_TOKENS", "8192")),
              "numeric_comparison": "Integer counts exact; float absolute tolerance 5e-7 (six decimal rounding).", "results": []}
    output.parent.mkdir(parents=True, exist_ok=True)
    for case in CASES:
        retrieved = retrieve_knowledge(case["question"])
        row = {**case, "retrieved": [m.card.id for m in retrieved.matches], "retrieval_passed": any(m.card.id == case["card"] for m in retrieved.matches), "arms": []}
        if "setup" in case:
            example = catalog[case["card"]].examples[0]
            row["reference_rows"] = readonly_query(case["setup"], example.query_sql)
            row["reference_passed"] = equal_rows(row["reference_rows"], case["expected"])
        report["results"].append(row)
        if live:
            manual = Selection("matched", version, (Match(catalog[case["card"]], 0, ()),))
            for arm, context in [("baseline", ""), ("manual", manual.prompt_context()), ("retrieved", retrieved.prompt_context())]:
                system = "你是数据分析方法顾问。区分给定数据与参考案例。明确前提、数据缺口和结论边界。不要编造来源。方法回答控制在500汉字以内。\n"
                question = case["question"]
                if "setup" in case:
                    system += '本轮为离线SQLite SQL生成测试，不调用工具。仅输出JSON对象 {"sql":"单条只读查询","limits":"结论边界"}，不得输出Markdown。\n'
                    question += "\n验证数据的结构和内容：\n" + case["setup"]
                result = {"arm": arm}
                try:
                    answer, finish, usage = model_call(system + context, question)
                    result.update(response=answer, finish_reason=finish, usage=usage)
                    if "setup" in case:
                        parsed = json.loads(answer)
                        rows = readonly_query(case["setup"], parsed["sql"])
                        result.update(rows=rows, execution_passed=equal_rows(rows, case["expected"]) and finish == "stop")
                    else:
                        result["review_status"] = "requires_semantic_review" if finish == "stop" and answer else "incomplete_response"
                except (OSError, ValueError, KeyError, TypeError, sqlite3.DatabaseError) as exc:
                    # Never print provider response bodies or credentials.
                    result.update(error_type=type(exc).__name__, execution_passed=False if "setup" in case else None)
                row["arms"].append(result)
                output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
                print(case["id"], arm, result.get("execution_passed", result.get("review_status", result.get("error_type"))), flush=True)
        output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print("Saved", output, flush=True)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--live", action="store_true")
    args = parser.parse_args()
    run(args.output, args.live)
