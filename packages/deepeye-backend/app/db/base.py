"""Database base classes and utilities."""

from sqlalchemy.orm import DeclarativeBase


# Use SQLAlchemy 2.0 style declarative base
class Base(DeclarativeBase):
    """Base class for all database models."""
    pass

