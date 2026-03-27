import uuid
from unittest.mock import MagicMock

from sqlalchemy import create_engine, text

from app.services.knowledge_base_service import search_kb_chunks


def test_search_kb_chunks_handles_sqlalchemy_row_results():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    with engine.connect() as conn:
        row = conn.execute(
            text(
                """
                SELECT 2 AS chunk_index,
                       'demo content' AS content,
                       '11111111-1111-1111-1111-111111111111' AS file_id,
                       'demo.md' AS filename,
                       0.75 AS score
                """
            )
        ).fetchone()

    fake_result = MagicMock()
    fake_result.fetchall.return_value = [row]

    db = MagicMock()
    db.execute.side_effect = [None, fake_result]

    results = search_kb_chunks(
        db,
        user_id=uuid.uuid4(),
        kb_ids=[uuid.uuid4()],
        query="demo query",
        top_k=3,
    )

    assert results == [
        {
            "file_id": "11111111-1111-1111-1111-111111111111",
            "filename": "demo.md",
            "chunk_index": 2,
            "content": "demo content",
        }
    ]
