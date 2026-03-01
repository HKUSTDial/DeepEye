import sqlite3

from deepeye.agents.nl2sql.value_retrieval.value_retrieval import ValueRetriever
from deepeye.datasource.datasource import ColumnMetadata, DatabaseMetadata, TableMetadata


def _build_empty_metadata() -> DatabaseMetadata:
    return DatabaseMetadata(
        name="demo",
        db_type="sqlite",
        tables=[
            TableMetadata(
                name="cities",
                columns=[
                    ColumnMetadata(name="country", type="TEXT"),
                    ColumnMetadata(name="city", type="TEXT"),
                ],
            )
        ],
    )


def test_retrieve_values_falls_back_to_live_db_when_metadata_has_no_examples(tmp_path) -> None:
    db_path = tmp_path / "demo.sqlite"

    conn = sqlite3.connect(str(db_path))
    conn.execute("CREATE TABLE cities (country TEXT, city TEXT)")
    conn.executemany(
        "INSERT INTO cities (country, city) VALUES (?, ?)",
        [
            ("China", "Beijing"),
            ("China", "Shanghai"),
            ("USA", "New York"),
        ],
    )
    conn.commit()
    conn.close()

    metadata = _build_empty_metadata()
    retriever = ValueRetriever(n_results=5, similarity_threshold=0.6, db_sample_limit=50)

    results = retriever.retrieve_values(
        keywords=["China", "Beijing"],
        metadata=metadata,
        database_path=str(db_path),
    )

    assert "cities" in results
    assert "country" in results["cities"]
    assert "city" in results["cities"]

    country_values = {item["value"] for item in results["cities"]["country"]}
    city_values = {item["value"] for item in results["cities"]["city"]}
    assert "China" in country_values
    assert "Beijing" in city_values


def test_retrieve_values_without_db_or_examples_returns_empty() -> None:
    metadata = _build_empty_metadata()
    retriever = ValueRetriever(n_results=5, similarity_threshold=0.6)

    results = retriever.retrieve_values(
        keywords=["China"],
        metadata=metadata,
        database_path=None,
    )

    assert results == {}
