"""
Telegram webhook endpoint.

Receives incoming updates from Telegram via POST requests.
The webhook URL is set via Telegram's setWebhook API.
"""

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_session
from app.core.logging import logger
from app.services.telegram import TelegramService

router = APIRouter(prefix="/telegram", tags=["telegram"])


@router.post("/webhook")
async def telegram_webhook(
    request: Request,
    x_telegram_bot_api_secret_token: str = Header(None),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """
    Receive Telegram bot updates via webhook.

    The request is verified using the secret token header.
    This endpoint is called by Telegram servers when users
    send messages to the bot.
    """
    # Verify the secret token
    if x_telegram_bot_api_secret_token != settings.WEBHOOK_SECRET:
        logger.warning("Invalid webhook secret token")
        raise HTTPException(status_code=403, detail="Forbidden")

    # Parse the update
    update = await request.json()
    logger.debug("Webhook received: %s", update)

    # Process the update
    service = TelegramService(session)
    result = await service.handle_update(update)

    return result