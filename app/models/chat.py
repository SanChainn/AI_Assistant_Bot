"""
Chat model.

Represents a conversation session between a user and the AI assistant.
A user can have multiple chats (conversation threads).
"""

import uuid
from typing import Optional

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Chat(Base):
    __tablename__ = "chats"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[Optional[str]] = mapped_column(
        String(256), nullable=True, comment="Auto-generated chat title"
    )
    telegram_chat_id: Mapped[Optional[int]] = mapped_column(
        nullable=True, comment="Telegram chat ID (for group chats)"
    )
    status: Mapped[str] = mapped_column(
        String(32), default="active", nullable=False, comment="active | archived | deleted"
    )
    metadata_json: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="JSON blob for chat metadata"
    )

    # Relationships
    user = relationship("User", back_populates="chats")
    messages = relationship("Message", back_populates="chat", cascade="all, delete-orphan")