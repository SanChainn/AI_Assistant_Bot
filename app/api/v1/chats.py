"""
Chat API endpoints.

Provides CRUD operations for user chats and message history.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.schemas.chat import ChatResponse
from app.schemas.message import MessageResponse
from app.services.chat import ChatService

router = APIRouter(prefix="/chats", tags=["chats"])


@router.get("/user/{user_id}", response_model=list[ChatResponse])
async def get_user_chats(
    user_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> list[ChatResponse]:
    """Get all active chats for a user."""
    service = ChatService(session)
    chats = await service.get_user_chats(user_id)
    return [ChatResponse.model_validate(c) for c in chats]


@router.get("/{chat_id}/messages", response_model=list[MessageResponse])
async def get_chat_messages(
    chat_id: UUID,
    limit: int = Query(50, ge=1, le=200),
    session: AsyncSession = Depends(get_session),
) -> list[MessageResponse]:
    """Get message history for a chat."""
    service = ChatService(session)
    messages = await service.get_chat_history(chat_id, limit)
    return [MessageResponse.model_validate(m) for m in messages]


@router.post("/{chat_id}/archive")
async def archive_chat(
    chat_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Archive a chat."""
    service = ChatService(session)
    result = await service.archive_chat(chat_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Chat not found")
    return {"ok": True, "chat_id": str(chat_id)}