"""
User service.

Contains business logic for user registration, lookup, and profile management.
Orchestrates between repositories and external APIs.
"""

from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.user import UserRepository
from app.schemas.user import UserCreate, UserUpdate


class UserService:
    """Service for user-related operations."""

    def __init__(self, session: AsyncSession) -> None:
        self._repo = UserRepository(session)

    async def register_or_update(self, data: UserCreate) -> dict:
        """
        Register a new user or update existing one from Telegram data.
        Returns the user as a dict.
        """
        user = await self._repo.get_by_telegram_id(data.telegram_id)
        if user is None:
            user = await self._repo.create(
                telegram_id=data.telegram_id,
                username=data.username,
                first_name=data.first_name,
                last_name=data.last_name,
                language_code=data.language_code,
                is_bot=data.is_bot,
            )
        else:
            user = await self._repo.update(
                user.id,
                username=data.username,
                first_name=data.first_name,
                last_name=data.last_name,
                language_code=data.language_code,
                last_interaction_at=datetime.now(timezone.utc),
            )
        return user

    async def get_by_telegram_id(self, telegram_id: int) -> Optional[dict]:
        """Get a user by Telegram ID."""
        user = await self._repo.get_by_telegram_id(telegram_id)
        return user

    async def get_by_id(self, user_id: UUID) -> Optional[dict]:
        """Get a user by UUID."""
        user = await self._repo.get(user_id)
        return user

    async def update_profile(self, user_id: UUID, data: UserUpdate) -> Optional[dict]:
        """Update user profile fields."""
        user = await self._repo.update(user_id, **data.model_dump(exclude_unset=True))
        return user

    async def get_preferences(self, user_id: UUID) -> dict:
        """Get user preferences as a dict."""
        user = await self._repo.get(user_id)
        if not user:
            return {}
        import json
        try:
            return json.loads(user.preferences) if user.preferences else {}
        except (json.JSONDecodeError, TypeError):
            return {}

    async def update_preferences(self, user_id: UUID, updates: dict) -> dict:
        """Merge updates into user preferences and persist to database."""
        current = await self.get_preferences(user_id)
        current.update(updates)
        import json
        await self._repo.update(user_id, preferences=json.dumps(current))
        return current
