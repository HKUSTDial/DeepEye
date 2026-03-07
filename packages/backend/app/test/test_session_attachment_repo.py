"""Tests for session attachment repository behavior."""

import os

os.environ.setdefault("ALLOW_INSECURE_DEFAULTS", "true")
os.environ.setdefault("LLM_API_KEY", "test-key")
os.environ.setdefault("LLM_BASE_URL", "http://localhost:8000")
os.environ.setdefault("LLM_MODEL", "test-model")

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models import Base, ChatSession, DataSource, User
from app.repositories import SessionAttachmentRepository


def _build_test_db():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    session_local = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    return session_local()


def _create_user(db, email: str = "alice@example.com") -> User:
    user = User(
        email=email,
        username="alice",
        hashed_password="hashed",
        is_active=True,
        is_superuser=False,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _create_session(db, user: User) -> ChatSession:
    session = ChatSession(user_id=user.id, title="Thread A")
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def _create_datasource(db, user: User, name: str = "warehouse") -> DataSource:
    datasource = DataSource(
        user_id=user.id,
        name=name,
        type="postgres",
        category="database",
        connection_string="postgresql://user:pass@localhost:5432/analytics",
    )
    db.add(datasource)
    db.commit()
    db.refresh(datasource)
    return datasource


def test_attach_lists_datasources_and_ids_once():
    db = _build_test_db()
    try:
        user = _create_user(db)
        session = _create_session(db, user)
        datasource = _create_datasource(db, user)
        repo = SessionAttachmentRepository(db)

        first = repo.attach(session.id, datasource.id)
        second = repo.attach(session.id, datasource.id)
        attached = repo.list_datasources(session.id)
        datasource_ids = repo.list_datasource_ids(session.id)

        assert first.id == second.id
        assert len(attached) == 1
        assert attached[0].id == datasource.id
        assert datasource_ids == [str(datasource.id)]
    finally:
        db.close()


def test_detach_and_cleanup_helpers():
    db = _build_test_db()
    try:
        user = _create_user(db)
        session = _create_session(db, user)
        datasource_a = _create_datasource(db, user, "warehouse-a")
        datasource_b = _create_datasource(db, user, "warehouse-b")
        repo = SessionAttachmentRepository(db)

        repo.attach(session.id, datasource_a.id)
        repo.attach(session.id, datasource_b.id)

        assert repo.detach(session.id, datasource_a.id) is True
        assert repo.detach(session.id, datasource_a.id) is False
        assert repo.list_datasource_ids(session.id) == [str(datasource_b.id)]
        assert repo.detach_all_for_session(session.id) == 1
        assert repo.list_datasource_ids(session.id) == []
    finally:
        db.close()
