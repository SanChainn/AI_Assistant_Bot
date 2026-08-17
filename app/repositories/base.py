"""
Base repository implementing the Repository Pattern.

Provides generic CRUD operations that all domain repositories inherit.
This keeps data access consistent and testable across the application.
"""

from typing import Generic, Optional, TypeVar

from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.base import Base

ModelT = TypeVar("ModelT", bound=Base)


class BaseRepository(Generic[ModelT]):
    """
    Generic repository with common CRUD operations.

    Usage:
        class UserRepository(BaseRepository[User]):
            pass
    """

    def __init__(self, session: AsyncSession, model: type[ModelT]) -> None:
        self._session = session
        self._model = model

    async def create(self, **kwargs) -> ModelT:
        """Create a new record."""
        instance = self._model(**kwargs)
        self._session.add(instance)
        await self._session.flush()
        return instance

    async def get(self, id) -> Optional[ModelT]:
        """Get a record by its primary key."""
        return await self._session.get(self._model, id)

    async def get_all(self, skip: int = 0, limit: int = 100) -> list[ModelT]:
        """Get all records with pagination."""
        stmt = select(self._model).offset(skip).limit(limit)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def update(self, id, **kwargs) -> Optional[ModelT]:
        """Update a record by its primary key."""
        stmt = (
            update(self._model)
            .where(self._model.id == id)
            .values(**kwargs)
            .returning(self._model)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def delete(self, id) -> bool:
        """Delete a record by its primary key. Returns True if deleted."""
        stmt = delete(self._model).where(self._model.id == id)
        result = await self._session.execute(stmt)
        return result.rowcount > 0