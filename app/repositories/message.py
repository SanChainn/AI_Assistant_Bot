"""
Message repository.

Provides data access for Message model with chat-scoped queries.
"""

from uuid import UUID

from sqlalchemy import select

from app.models.message import Message
from app.repositories.base import BaseRepository


class MessageRepository(BaseRepository[Message]):
    """Repository for message data access."""

    def __init__(self, session) -> None:
        super().__init__(session, Message)

    async def get_by_chat(
        self, chat_id: UUID, skip: int = 0, limit: int = 100
    ) -> list[Message]:
        """Get all messages in a chat, ordered by creation time."""
        stmt = (
            select(Message)
            .where(Message.chat_id == chat_id)
            .offset(skip)
            .limit(limit)
            .order_by(Message.created_at.asc())
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_chat_history(
        self, chat_id: UUID, limit: int = 50
    ) -> list[Message]:
        """Get the most recent messages for LLM context."""
        stmt = (
            select(Message)
            .where(Message.chat_id == chat_id)
            .order_by(Message.created_at.desc())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return list(reversed(result.scalars().all()))