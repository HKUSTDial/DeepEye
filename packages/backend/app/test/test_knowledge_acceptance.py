"""Guard the evaluation executor and expected-answer comparison."""

import sqlite3

import pytest
from app.knowledge import acceptance


@pytest.mark.parametrize("query", [
    "DROP TABLE sample", "DELETE FROM sample", "ATTACH DATABASE '/tmp/other.db' AS other",
    "PRAGMA database_list", "SELECT load_extension('anything')", "SELECT randomblob(1000000000)",
    "SELECT 1; SELECT 2",
])
def test_model_sql_cannot_write_attach_or_allocate_arbitrary_blobs(query):
    with pytest.raises(sqlite3.DatabaseError):
        acceptance.readonly_query("CREATE TABLE sample(x INTEGER);", query)


def test_sql_can_aggregate_and_reference_checks_catch_wrong_answers():
    actual = acceptance.readonly_query("CREATE TABLE sample(x INTEGER); INSERT INTO sample VALUES(1),(2);", "SELECT AVG(x),COUNT(*) FROM sample")
    assert acceptance.equal_rows(actual, [[1.5, 2]])
    assert not acceptance.equal_rows(actual, [[1.6, 2]])
    assert not acceptance.equal_rows(actual, [[1.5]])
    assert not acceptance.equal_rows([], [[1.5, 2]])
    assert acceptance.equal_rows([[3, 1, .333333]], [[3, 1, 1 / 3]])
    assert not acceptance.equal_rows([[3, 1, .33]], [[3, 1, 1 / 3]])


def test_all_fixture_answers_match_curated_sql():
    cards = {c.id: c for c in acceptance.load_catalog()[0]}
    for case in acceptance.CASES:
        if "setup" in case:
            rows = acceptance.readonly_query(case["setup"], cards[case["card"]].examples[0].query_sql)
            assert acceptance.equal_rows(rows, case["expected"]), case["id"]
