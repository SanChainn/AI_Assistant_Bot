"""
LLM API endpoints.

Provides direct access to the LLM for testing and debugging.
The primary chat interface is via Telegram webhook.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.logging import logger
from app.schemas.llm import ChatRequest, ChatResponse
from app.schemas.message import MessageCreate
from app.services.chat import ChatService
from app.services.conversation import ConversationService

router = APIRouter(prefix="/llm", tags=["llm"])


@router.post("/chat", response_model=ChatResponse)
async def chat_with_llm(
    request: ChatRequest,
    session: AsyncSession = Depends(get_session),
) -> ChatResponse:
    """
    Send a message to the AI assistant and get a response.

    This is a direct API for testing. The primary interface
    is the Telegram webhook.
    """
    # Verify the chat exists
    chat_service = ChatService(session)
    chat = await chat_service.get_chat(request.chat_id)
    if chat is None:
        raise HTTPException(status_code=404, detail="Chat not found")

    # Save the user message
    message_data = MessageCreate(
        chat_id=request.chat_id,
        user_id=chat.user_id,
        role="user",
        content=request.message,
    )
    user_message = await chat_service.add_message(message_data)

    # Generate AI response
    conversation_service = ConversationService(session)
    try:
        ai_content = await conversation_service.generate_response(
            chat_id=request.chat_id,
            user_message_id=user_message.id,
        )
    except Exception as e:
        logger.error("LLM chat failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))

    return ChatResponse(
        response=ai_content,
        model="deepseek/deepseek-chat-v4-flash",
        total_tokens=0,
    )