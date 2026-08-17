"""
User model.

Represents a user of the AI assistant, linked to their Telegram identity.
"""

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import BigInteger, Boolean, DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class User(Base):
    __tablename__ = "users"

    telegram_id: Mapped[int] = mapped_column(
        BigInteger, unique=True, nullable=False, index=True
    )
    username: Mapped[Optional[str]] = mapped_column(
        String(128), nullable=True, index=True
    )
    first_name: Mapped[Optional[str]] = mapped_column(
        String(128), nullable=True
    )
    last_name: Mapped[Optional[str]] = mapped_column(
        String(128), nullable=True
    )
    language_code: Mapped[Optional[str]] = mapped_column(
        String(8), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )
    is_bot: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    last_interaction_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    preferences: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="JSON blob for user preferences"
    )

    # Relationships
    chats = relationship("Chat", back_populates="user", cascade="all, delete-orphan")
    messages = relationship("Message", back_populates="user", cascade="all, delete-orphan")