"""
Chat service.

Contains business logic for managing conversations.
Orchestrates between chat and message repositories.
"""

from typing import Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.chat import ChatRepository
from app.repositories.message import MessageRepository
from app.schemas.chat import ChatCreate, ChatUpdate
from app.schemas.message import MessageCreate


class ChatService:
    """Service for chat and message operations."""

    def __init__(self, session: AsyncSession) -> None:
        self._chat_repo = ChatRepository(session)
        self._msg_repo = MessageRepository(session)

    async def get_chat(self, chat_id: UUID) -> Optional[dict]:
        """Get a single chat by ID."""
        return await self._chat_repo.get(chat_id)

    async def get_or_create_dm(self, user_id: UUID, telegram_chat_id: int) -> dict:
        """Get or create a direct message chat."""
        chat = await self._chat_repo.get_or_create_dm(user_id, telegram_chat_id)
        return chat

    async def get_user_chats(self, user_id: UUID) -> list:
        """Get all active chats for a user."""
        return await self._chat_repo.get_by_user(user_id)

    async def add_message(self, data: MessageCreate) -> dict:
        """Add a message to a chat."""
        message = await self._msg_repo.create(**data.model_dump())
        return message

    async def get_chat_history(self, chat_id: UUID, limit: int = 50) -> list:
        """Get conversation history for LLM context."""
        return await self._msg_repo.get_chat_history(chat_id, limit)

    async def archive_chat(self, chat_id: UUID) -> Optional[dict]:
        """Archive a chat."""
        return await self._chat_repo.update(chat_id, status="archived")