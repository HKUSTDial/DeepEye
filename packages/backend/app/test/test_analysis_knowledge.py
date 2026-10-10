"""Behavior checks for the local, source-grounded case library (no LLM)."""

import json

import pytest
from app.knowledge.retrieval import load_catalog, retrieve_knowledge


@pytest.mark.parametrize(
    ("question", "expected"),
    [
        ("模块CTR下降了，但曝光涨了，应该怎么查？", "C02"),
        ("The experiment has a sample ratio mismatch after bot filtering", "C01"),
        ("新用户次日留存怎么算？", "M02"),
        ("注册到支付的漏斗转化在哪里流失？", "M01"),
        ("客户端埋点上报数量突变", "C03"),
        ("各分群都改善但整体没变化", "C04"),
        ("实验不显著就说明没有影响吗？", "C05"),
        ("用户级实验每天看p值，显著就提前停止", "C06"),
        ("几个功能的季度收益可以相加吗？", "C07"),
        ("检查用户随机分配比例是否偏离设计", "C01"),
    ],
)
def test_business_questions_retrieve_relevant_case(question, expected):
    selection = retrieve_knowledge(question)
    assert expected in [match.card.id for match in selection.matches]
    assert selection.status == "matched"
    assert selection.catalog_version
    assert expected in selection.prompt_context()


@pytest.mark.parametrize("question", ["你好", "", "计算销售额总和", "describe abstract syntax trees"])
def test_unrelated_questions_do_not_force_a_case(question):
    selection = retrieve_knowledge(question)
    assert selection.status == "no_match"
    assert not selection.matches
    assert "No matching" in selection.prompt_context()


def test_short_english_tags_match_words_not_substrings():
    assert not retrieve_knowledge("control infrastructure abstract").matches
    assert retrieve_knowledge("CTR").matches[0].card.id == "C02"


def test_context_budget_keeps_complete_cards_and_provenance():
    selection = retrieve_knowledge("CTR 留存 漏斗 SRM 不显著 埋点 分群", max_cards=2)
    assert len(selection.matches) == 2
    for match in selection.matches:
        assert match.card.sources[0].url in selection.prompt_context()
    assert not retrieve_knowledge("CTR", max_chars=1).matches


def test_disabled_retrieval_does_not_even_read_missing_catalog(tmp_path):
    selection = retrieve_knowledge("CTR", enabled=False, catalog_path=tmp_path / "missing.json")
    assert selection.status == "disabled"
    assert selection.prompt_context() == ""


def test_missing_or_corrupt_catalog_falls_back_without_exposing_contents(tmp_path):
    path = tmp_path / "catalog.json"
    assert retrieve_knowledge("CTR", catalog_path=path).status == "unavailable"
    path.write_text('{"secret": invalid}', encoding="utf-8")
    result = retrieve_knowledge("CTR", catalog_path=path)
    assert result.status == "unavailable"
    assert "secret" not in json.dumps(result.trace())
    assert "unavailable" in result.prompt_context()


def test_catalog_rejects_duplicates_and_unsafe_source_links(tmp_path):
    catalog, _ = load_catalog()
    path = tmp_path / "catalog.json"
    record = catalog[0].model_dump()
    path.write_text(json.dumps([record, record]), encoding="utf-8")
    with pytest.raises(ValueError, match="Duplicate"):
        load_catalog(path)
    record["sources"][0]["url"] = "javascript:alert(1)"
    path.write_text(json.dumps([record]), encoding="utf-8")
    with pytest.raises(ValueError):
        load_catalog(path)


def test_trace_distinguishes_retrieval_from_validation_and_excludes_query():
    query = "CTR secret-customer-123"
    trace = retrieve_knowledge(query).trace()
    assert trace["assessment"] == "retrieved_not_adopted_or_validated"
    assert trace["matches"][0]["id"] == "C02"
    assert "secret-customer-123" not in json.dumps(trace)
    assert trace["matches"][0]["matched_terms"]
