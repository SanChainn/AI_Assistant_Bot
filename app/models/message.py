"""
Message model.

Represents a single message in a conversation.
Messages can be from the user or the AI assistant.
"""

import uuid
from typing import Optional

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Message(Base):
    __tablename__ = "messages"

    chat_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("chats.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    role: Mapped[str] = mapped_column(
        String(32), nullable=False, comment="user | assistant | system"
    )
    content: Mapped[str] = mapped_column(
        Text, nullable=False
    )
    telegram_message_id: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True, comment="Original Telegram message ID"
    )
    metadata_json: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="JSON blob for message metadata (tokens, model, etc.)"
    )

    # Relationships
    chat = relationship("Chat", back_populates="messages")
    user = relationship("User", back_populates="messages")