"""
Chat schemas for API request/response validation.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class ChatCreate(BaseModel):
    """Schema for creating a new chat."""
    user_id: UUID
    telegram_chat_id: Optional[int] = None
    title: Optional[str] = None


class ChatResponse(BaseModel):
    """Schema for chat API responses."""
    id: UUID
    user_id: UUID
    title: Optional[str] = None
    telegram_chat_id: Optional[int] = None
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ChatUpdate(BaseModel):
    """Schema for updating a chat."""
    title: Optional[str] = None
    status: Optional[str] = None