"""
LLM schemas for API request/response validation.
"""

from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """Schema for sending a chat message to the LLM."""
    chat_id: UUID
    message: str = Field(..., min_length=1, max_length=4096)


class ChatResponse(BaseModel):
    """Schema for LLM chat response."""
    response: str
    model: str = ""
    total_tokens: int = 0