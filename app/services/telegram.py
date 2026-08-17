"""
Telegram webhook service.

Handles incoming Telegram updates (messages, commands).
This is the entry point for all user interactions via Telegram.
Now wired to the LLM for AI response generation.
Also handles Google Calendar OAuth flow.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.client import bot_client
from app.core.logging import logger
from app.schemas.message import MessageCreate
from app.schemas.user import UserCreate
from app.services.chat import ChatService
from app.services.conversation import ConversationService
from app.services import google_calendar
from app.services.user import UserService
from app.repositories.user import UserRepository
from app.tools.base import update_user_preferences
from app.api.v1.auth import store_pending_oauth


class TelegramService:
    """
    Orchestrates Telegram webhook processing.

    Flow:
    1. Parse incoming update
    2. Register/update user
    3. Get or create chat
    4. Save user message
    5. Send typing indicator
    6. Call LLM for response
    7. Save AI response and send it back to user
    """

    def __init__(self, session: AsyncSession) -> None:
        self._user_service = UserService(session)
        self._chat_service = ChatService(session)
        self._conversation_service = ConversationService(session)

    async def handle_update(self, update: dict) -> dict:
        """
        Process an incoming Telegram update.

        Handles text messages by:
        - Registering/updating the user
        - Creating/finding a chat
        - Saving the user message
        - Generating an AI response via LLM
        - Saving and sending the AI response
        """
        logger.debug("Received update: %s", update)

        # Extract message data
        message = update.get("message", {})
        if not message:
            logger.warning("No message in update")
            return {"ok": False, "error": "no_message"}

        chat_data = message.get("chat", {})
        from_user = message.get("from", {})

        # Ignore bot's own messages
        if from_user.get("is_bot"):
            return {"ok": False, "error": "bot_message"}

        # 1. Register or update user
        user_data = UserCreate(
            telegram_id=from_user.get("id"),
            username=from_user.get("username"),
            first_name=from_user.get("first_name"),
            last_name=from_user.get("last_name"),
            language_code=from_user.get("language_code"),
            is_bot=from_user.get("is_bot", False),
        )
        user = await self._user_service.register_or_update(user_data)

        # Load user preferences from database into in-memory cache
        # so tools can access Google Calendar tokens
        db_prefs = await self._user_service.get_preferences(user.id)
        logger.debug(
            "Loading prefs for user_id=%s (type=%s): keys=%s",
            user.id, type(user.id).__name__, list(db_prefs.keys()) if db_prefs else "empty",
        )
        if db_prefs:
            update_user_preferences(str(user.id), db_prefs)
            logger.debug("In-memory prefs updated for key=%s", str(user.id))

        # 2. Get or create DM chat
        telegram_chat_id = chat_data.get("id")
        chat = await self._chat_service.get_or_create_dm(
            user_id=user.id,
            telegram_chat_id=telegram_chat_id,
        )

        # 3. Save user message
        text = message.get("text", "")

        # Handle commands — support both underscore and no-underscore variants
        text_lower = text.lower().strip()

        if text_lower in ("/start", "/start@sanchaintun_bot"):
            reply = (
                "Hello! I'm your AI Personal Assistant. 🤖\n\n"
                "I can help you with:\n"
                "• Answering questions\n"
                "• Managing your calendar\n"
                "• Sending emails\n"
                "• Remembering information\n\n"
                "Commands:\n"
                "/connectcalendar - Connect Google Calendar\n"
                "/disconnectcalendar - Disconnect Google Calendar\n"
                "/help - Show this message"
            )
            await bot_client.send_message(chat_id=telegram_chat_id, text=reply)
            return {"ok": True, "user_id": str(user.id), "chat_id": str(chat.id), "command": "start"}

        if text_lower in ("/help", "/help@sanchaintun_bot"):
            reply = (
                "Available commands:\n\n"
                "/connectcalendar - Connect your Google Calendar\n"
                "   -> I'll send you a link to authorize\n"
                "   -> Open it, sign in, and send me the code\n"
                "/disconnectcalendar - Remove Google Calendar access\n"
                "/start - Welcome message\n"
                "/help - This message\n\n"
                "Or just chat with me naturally!"
            )
            await bot_client.send_message(chat_id=telegram_chat_id, text=reply)
            return {"ok": True, "user_id": str(user.id), "chat_id": str(chat.id), "command": "help"}

        if text_lower in ("/connect_calendar", "/connectcalendar", "/connect_calendar@sanchaintun_bot", "/connectcalendar@sanchaintun_bot"):
            try:
                # Generate a unique state parameter that maps to this Telegram chat
                import secrets
                state = secrets.token_hex(16)
                store_pending_oauth(state, telegram_chat_id)

                auth_url = google_calendar.get_auth_url(state=state)
                # Use HTML parse_mode with explicit <a> tag to prevent URL truncation
                reply = (
                    "🌐 <b>Connect Google Account</b>\n\n"
                    "Click the button below to authorize Google Calendar & Gmail:\n\n"
                    f'<a href="{auth_url}">🔗 Connect Google Account</a>\n\n'
                    "After you sign in, Google will redirect you back automatically "
                    "and I'll be notified! 🎉"
                )
                # Send with HTML parse mode to preserve the full URL in the hyperlink
                await bot_client._call(
                    "sendMessage",
                    chat_id=telegram_chat_id,
                    text=reply,
                    parse_mode="HTML",
                )
            except Exception as e:
                logger.error("Failed to generate auth URL: %s", e)
                await bot_client.send_message(
                    chat_id=telegram_chat_id,
                    text=f"Sorry, I couldn't generate the authorization link. Error: {e}",
                )
            return {"ok": True, "user_id": str(user.id), "chat_id": str(chat.id), "command": "connect_calendar"}

        if text_lower in ("/disconnect_calendar", "/disconnectcalendar", "/disconnect_calendar@sanchaintun_bot", "/disconnectcalendar@sanchaintun_bot"):
            user_id_str = str(user.id)
            update_user_preferences(user_id_str, {"google_calendar_tokens": {"connected": False}})
            await bot_client.send_message(
                chat_id=telegram_chat_id,
                text="Google Calendar has been disconnected. You can reconnect anytime with /connectcalendar",
            )
            return {"ok": True, "user_id": str(user.id), "chat_id": str(chat.id), "command": "disconnect_calendar"}

        # Check if this is an OAuth code exchange (starts with "4/")
        if text and text.strip().startswith("4/") and not text.startswith("/"):
            user_id_str = str(user.id)
            try:
                token_data = google_calendar.exchange_code(text.strip())
                # Persist to both in-memory cache and database
                update_user_preferences(user_id_str, {"google_calendar_tokens": token_data})
                await self._user_service.update_preferences(
                    user.id, {"google_calendar_tokens": token_data}
                )
                await bot_client.send_message(
                    chat_id=telegram_chat_id,
                    text="✅ Google connected successfully! Now you can use:\n\n"
                         "📅 Calendar:\n"
                         "• \"Create an event tomorrow at 3pm\"\n"
                         "• \"What's on my calendar?\"\n\n"
                         "📧 Email:\n"
                         "• \"Send an email to ...\"\n"
                         "• \"Check my inbox\"\n\n"
                         "Both Calendar and Gmail are now connected!",
                )
                return {"ok": True, "user_id": str(user.id), "chat_id": str(chat.id), "command": "oauth_code"}
            except Exception as e:
                logger.error("OAuth code exchange failed: %s", e)
                await bot_client.send_message(
                    chat_id=telegram_chat_id,
                    text=f"❌ Failed to connect Google Calendar: {e}\n\nPlease try /connect_calendar again.",
                )
                return {"ok": False, "error": f"oauth_failed: {e}"}

        # 4. Save user message for AI processing
        user_message = None
        if text:
            message_data = MessageCreate(
                chat_id=chat.id,
                user_id=user.id,
                role="user",
                content=text,
                telegram_message_id=message.get("message_id"),
            )
            user_message = await self._chat_service.add_message(message_data)
            logger.info(
                "Saved message from user %s in chat %s: %s",
                user.telegram_id, chat.id, text[:50],
            )

        # 5. Send typing indicator
        await bot_client.send_typing(telegram_chat_id)

        # 6. Generate AI response via LLM
        ai_content = ""
        if text and user_message:
            try:
                ai_content = await self._conversation_service.generate_response(
                    chat_id=chat.id,
                    user_message_id=user_message.id,
                )
            except Exception as e:
                logger.error("LLM generation failed: %s", e)
                ai_content = "I'm sorry, I encountered an error processing your request."

        # 7. Send AI response back to Telegram
        if ai_content:
            await bot_client.send_message(
                chat_id=telegram_chat_id,
                text=ai_content,
            )

        return {
            "ok": True,
            "user_id": str(user.id),
            "chat_id": str(chat.id),
            "response_length": len(ai_content),
        }
