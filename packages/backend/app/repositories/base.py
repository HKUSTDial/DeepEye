"""Base Repository abstraction and SQLAlchemy implementation."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Generic, TypeVar
from uuid import UUID

from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.db.session import Base

T = TypeVar("T")
ID = TypeVar("ID", str, UUID, int)


class BaseRepository(ABC, Generic[T, ID]):
    """Abstract repository for aggregate persistence."""

    @abstractmethod
    def get(self, id: ID) -> T | None: ...

    @abstractmethod
    def save(self, entity: T) -> T: ...

    @abstractmethod
    def delete(self, id: ID) -> None: ...

    @abstractmethod
    def find_all(self, skip: int = 0, limit: int = 100) -> list[T]: ...


ModelT = TypeVar("ModelT", bound=Base)


class SQLAlchemyRepository(BaseRepository[ModelT, ID], Generic[ModelT, ID]):
    """Generic SQLAlchemy repository implementing BaseRepository."""

    def __init__(self, db: Session, model_class: type[ModelT]):
        self.db = db
        self.model_class = model_class

    def get(self, id: ID) -> ModelT | None:
        return self.db.query(self.model_class).filter(self.model_class.id == id).first()

    def save(self, entity: ModelT) -> ModelT:
        self.db.add(entity)
        self.db.commit()
        self.db.refresh(entity)
        return entity

    def delete(self, id: ID) -> None:
        entity = self.get(id)
        if entity:
            self.db.delete(entity)
            self.db.commit()

    def find_all(self, skip: int = 0, limit: int = 100) -> list[ModelT]:
        return self.db.query(self.model_class).offset(skip).limit(limit).all()

    def find_all_desc(self, order_by: str, skip: int = 0, limit: int = 100) -> list[ModelT]:
        """Find all with descending order."""
        col = getattr(self.model_class, order_by)
        return (
            self.db.query(self.model_class)
            .order_by(desc(col))
            .offset(skip)
            .limit(limit)
            .all()
        )

