"""Base repository with generic CRUD operations."""

from typing import Any, Generic, TypeVar
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.database.base import Base

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    """Generic repository with async CRUD operations.

    Provides standard database operations for any SQLAlchemy model.
    """

    def __init__(self, model: type[ModelType], session: AsyncSession) -> None:
        """Initialize repository.

        Args:
            model: SQLAlchemy model class
            session: Async database session
        """
        self.model = model
        self.session = session

    async def get(self, id: UUID) -> ModelType | None:
        """Get single record by ID.

        Args:
            id: Record UUID

        Returns:
            Model instance or None if not found
        """
        return await self.session.get(self.model, id)

    async def get_all(self, skip: int = 0, limit: int = 100) -> list[ModelType]:
        """Get all records with pagination.

        Args:
            skip: Number of records to skip
            limit: Maximum records to return

        Returns:
            List of model instances
        """
        stmt = select(self.model).offset(skip).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def create(self, **kwargs: Any) -> ModelType:
        """Create new record.

        Args:
            **kwargs: Model field values

        Returns:
            Created model instance
        """
        instance = self.model(**kwargs)
        self.session.add(instance)
        await self.session.flush()
        await self.session.refresh(instance)
        return instance

    async def delete(self, id: UUID) -> bool:
        """Delete record by ID.

        Args:
            id: Record UUID

        Returns:
            True if deleted, False if not found
        """
        instance = await self.get(id)
        if instance is None:
            return False

        await self.session.delete(instance)
        await self.session.flush()
        return True
