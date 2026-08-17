"""
Chat repository.

Provides data access for Chat model with user-scoped queries.
"""

from typing import Optional
from uuid import UUID

from sqlalchemy import select

from app.models.chat import Chat
from app.repositories.base import BaseRepository


class ChatRepository(BaseRepository[Chat]):
    """Repository for chat data access."""

    def __init__(self, session) -> None:
        super().__init__(session, Chat)

    async def get_by_user(self, user_id: UUID, skip: int = 0, limit: int = 50) -> list[Chat]:
        """Get all active chats for a user."""
        stmt = (
            select(Chat)
            .where(Chat.user_id == user_id, Chat.status == "active")
            .offset(skip)
            .limit(limit)
            .order_by(Chat.updated_at.desc())
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_or_create_dm(self, user_id: UUID, telegram_chat_id: int) -> Chat:
        """Find or create a direct message chat for a user."""
        stmt = select(Chat).where(
            Chat.user_id == user_id,
            Chat.telegram_chat_id == telegram_chat_id,
            Chat.status == "active",
        )
        result = await self._session.execute(stmt)
        chat = result.scalar_one_or_none()
        if chat is None:
            chat = await self.create(
                user_id=user_id,
                telegram_chat_id=telegram_chat_id,
                title="Direct Message",
            )
        return chat