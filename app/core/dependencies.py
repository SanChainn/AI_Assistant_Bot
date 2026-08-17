"""
Dependency Injection container.

Centralizes all dependencies so that services, repositories, and clients
can be injected cleanly without importing infrastructure directly into
business logic.
"""

from typing import Optional

from redis.asyncio import Redis as AsyncRedis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session as _get_session
from app.core.redis import get_redis as _get_redis


class Dependencies:
    """
    Dependency injection container.

    Provides access to infrastructure components through a single
    point of entry, making it easy to swap implementations for
    testing or future changes.
    """

    def __init__(self) -> None:
        self._session: Optional[AsyncSession] = None
        self._redis: Optional[AsyncRedis] = None

    async def get_db(self) -> AsyncSession:
        """Get the current database session."""
        if self._session is None:
            gen = _get_session()
            self._session = await gen.__anext__()
        return self._session

    async def get_redis(self) -> AsyncRedis:
        """Get the current Redis client."""
        if self._redis is None:
            self._redis = await _get_redis()
        return self._redis


# Singleton instance
deps = Dependencies()