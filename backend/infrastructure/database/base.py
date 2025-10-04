"""SQLAlchemy declarative base and shared database utilities."""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models.

    Provides:
    - Declarative base for model inheritance
    - Type hints for mapped columns
    - Shared model utilities
    """

    pass
