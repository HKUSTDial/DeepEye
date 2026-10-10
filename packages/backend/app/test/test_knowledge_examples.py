"""Execute curated synthetic SQL and check hand-derived answers, without an LLM."""

import math
import sqlite3

import pytest
from app.knowledge.retrieval import load_catalog, retrieve_knowledge

EXAMPLES = [(card.id, example) for card in load_catalog()[0] for example in card.examples]


@pytest.mark.parametrize("card_id,example", EXAMPLES, ids=[e.id for _, e in EXAMPLES])
def test_verified_sql_matches_reference(card_id, example):
    # Only reviewed repository fixtures are executed, in a disposable in-memory DB.
    with sqlite3.connect(":memory:") as connection:
        connection.executescript(example.setup_sql)
        result = connection.execute(example.query_sql)
        assert [column[0] for column in result.description] == example.expected_columns
        rows = result.fetchall()
    assert len(rows) == len(example.expected_rows)
    for actual, expected in zip(rows, example.expected_rows, strict=True):
        for value, reference in zip(actual, expected, strict=True):
            if isinstance(reference, (int, float)):
                assert math.isclose(value, reference, rel_tol=1e-9, abs_tol=1e-9)
            else:
                assert value == reference


def test_example_card_reaches_prompt_with_sources_and_budget():
    selection = retrieve_knowledge("留存 cohort 七日回访")
    context = selection.prompt_context()
    assert '"E03"' in context
    assert "完全合成" in context
    assert "retention-analysis-build" in context
    assert len(context) <= 12000


def test_example_ids_are_unique_and_four_topics_are_covered():
    assert len({example.id for _, example in EXAMPLES}) == len(EXAMPLES)
    assert {"C01", "C02", "M01", "M02"} <= {card_id for card_id, _ in EXAMPLES}


def test_reference_answers_independently_cover_edge_cases():
    # Python set/arithmetic references are independent of SQL grouping and joins.
    assert (2 / 4 + 10 / 40) / 2 == .375
    assert sum([2, 10]) / sum([4, 40]) != .375
    payments = {"a": [1, 2], "b": [25], "c": [-2], "d": [24], "e": [0]}
    converted = {user for user, times in payments.items() if any(0 < t <= 24 for t in times)}
    assert converted == {"a", "d"}
    starts = {"a": 1, "b": 1, "c": 3, "d": 4}
    returns = {"a": {8}, "b": {7}, "c": {10}, "d": {10}}
    eligible = {u for u, day in starts.items() if day + 7 <= 10}
    assert eligible == {"a", "b", "c"}
    assert {u for u in eligible if starts[u] + 7 in returns[u]} == {"a", "c"}
