"""
Telegram Bot HTTP client.

Communicates with the Telegram Bot API using httpx.
All methods are async and use the bot token from settings.
"""

from typing import Optional

import httpx

from app.core.config import settings
from app.core.logging import logger


class TelegramBotClient:
    """
    Async HTTP client for the Telegram Bot API.

    Sends messages, edits, and performs bot operations.
    No state is stored here — this is a stateless HTTP client.
    """

    BASE_URL = "https://api.telegram.org/bot{token}/{method}"

    def __init__(self) -> None:
        self._token = settings.TELEGRAM_BOT_TOKEN
        self._http = httpx.AsyncClient(timeout=30.0)

    async def _call(self, method: str, **kwargs) -> dict:
        """Call a Telegram Bot API method."""
        url = self.BASE_URL.format(token=self._token, method=method)
        try:
            response = await self._http.post(url, json=kwargs)
            response.raise_for_status()
            result = response.json()
            if not result.get("ok"):
                logger.error("Telegram API error: %s", result)
            return result
        except httpx.HTTPError as e:
            logger.error("Telegram HTTP error: %s", e)
            return {"ok": False, "error": str(e)}

    async def send_message(
        self,
        chat_id: int,
        text: str,
        parse_mode: Optional[str] = "Markdown",
        reply_to_message_id: Optional[int] = None,
    ) -> dict:
        """Send a text message to a Telegram chat.

        If Markdown parsing fails, automatically retries as plain text.
        """
        payload = {
            "chat_id": chat_id,
            "text": text,
        }
        if parse_mode:
            payload["parse_mode"] = parse_mode
        if reply_to_message_id:
            payload["reply_to_message_id"] = reply_to_message_id

        result = await self._call("sendMessage", **payload)

        # If Markdown parsing failed, retry without parse_mode
        if not result.get("ok") and parse_mode:
            logger.warning("Markdown parse failed, retrying as plain text")
            payload.pop("parse_mode", None)
            result = await self._call("sendMessage", **payload)

        return result

    async def send_typing(self, chat_id: int) -> dict:
        """Send a 'typing' chat action indicator."""
        return await self._call(
            "sendChatAction",
            chat_id=chat_id,
            action="typing",
        )

    async def set_webhook(self, url: str) -> dict:
        """Set or update the bot webhook URL.

        If WEBHOOK_SECRET is configured, Telegram will echo it back in the
        X-Telegram-Bot-Api-Secret-Token header of every update so the
        webhook endpoint can verify the request origin.
        """
        payload: dict = {"url": url}
        if settings.WEBHOOK_SECRET:
            payload["secret_token"] = settings.WEBHOOK_SECRET
        return await self._call("setWebhook", **payload)

    async def delete_webhook(self) -> dict:
        """Remove the current webhook."""
        return await self._call("deleteWebhook")

    async def get_webhook_info(self) -> dict:
        """Get current webhook status."""
        return await self._call("getWebhookInfo")

    async def close(self) -> dict:
        """Close the HTTP client."""
        return await self._http.aclose()


# Singleton instance
bot_client = TelegramBotClient()