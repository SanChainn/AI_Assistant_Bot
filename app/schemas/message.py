"""
Message schemas for API request/response validation.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class MessageCreate(BaseModel):
    """Schema for creating a new message."""
    chat_id: UUID
    user_id: UUID
    role: str  # user | assistant | system
    content: str
    telegram_message_id: Optional[int] = None


class MessageResponse(BaseModel):
    """Schema for message API responses."""
    id: UUID
    chat_id: UUID
    user_id: UUID
    role: str
    content: str
    telegram_message_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}