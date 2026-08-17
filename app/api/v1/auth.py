"""
Google OAuth callback endpoint.

Handles the redirect from Google after the user authorizes.
Exchanges the code for tokens, stores them in the user's preferences,
and notifies the user via Telegram.

This is a web-based OAuth flow:
1. User sends /connectcalendar
2. Bot sends a link with a state parameter (maps to Telegram chat ID)
3. User clicks link, authorizes in browser
4. Google redirects to /api/v1/auth/google/callback
5. The callback exchanges the code, stores tokens, notifies the user
"""

from fastapi import APIRouter, Query
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.client import bot_client
from app.core.database import get_session
from app.core.logging import logger
from app.services import google_calendar
from app.services.user import UserService
from app.tools.base import update_user_preferences

router = APIRouter(prefix="/auth", tags=["auth"])

# In-memory map: state -> telegram_chat_id
# Set by TelegramService when generating the OAuth URL
_pending_oauth: dict[str, int] = {}


def store_pending_oauth(state: str, telegram_chat_id: int) -> None:
    """Store a pending OAuth state mapped to a Telegram chat ID."""
    _pending_oauth[state] = telegram_chat_id


SUCCESS_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Connected!</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            display: flex; justify-content: center; align-items: center;
            min-height: 100vh; margin: 0; background: #f0f2f5;
        }}
        .card {{
            background: white; border-radius: 16px; padding: 40px;
            box-shadow: 0 4px 24px rgba(0,0,0,0.1); text-align: center;
            max-width: 400px;
        }}
        .checkmark {{
            width: 64px; height: 64px; background: #22c55e; border-radius: 50%;
            display: flex; align-items: center; justify-content: center;
            margin: 0 auto 20px; font-size: 32px; color: white;
        }}
        h1 {{ color: #1a1a2e; margin-bottom: 8px; }}
        p {{ color: #666; line-height: 1.6; }}
    </style>
</head>
<body>
    <div class="card">
        <div class="checkmark">✓</div>
        <h1>Google Connected!</h1>
        <p>Your Google Calendar is now linked to your AI Assistant.<br>
        You can close this window and return to Telegram.</p>
    </div>
</body>
</html>"""

ERROR_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Connection Failed</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            display: flex; justify-content: center; align-items: center;
            min-height: 100vh; margin: 0; background: #f0f2f5;
        }}
        .card {{
            background: white; border-radius: 16px; padding: 40px;
            box-shadow: 0 4px 24px rgba(0,0,0,0.1); text-align: center;
            max-width: 400px;
        }}
        .xmark {{
            width: 64px; height: 64px; background: #ef4444; border-radius: 50%;
            display: flex; align-items: center; justify-content: center;
            margin: 0 auto 20px; font-size: 32px; color: white;
        }}
        h1 {{ color: #1a1a2e; margin-bottom: 8px; }}
        p {{ color: #666; line-height: 1.6; }}
    </style>
</head>
<body>
    <div class="card">
        <div class="xmark">✕</div>
        <h1>Connection Failed</h1>
        <p>{error}</p>
    </div>
</body>
</html>"""


@router.get("/google/callback")
async def google_callback(
    code: str = Query(""),
    state: str = Query(""),
    error: str = Query(""),
):
    """
    Google OAuth callback endpoint.

    Google redirects here after the user authorizes.
    The `state` parameter maps to the Telegram chat ID.
    The `code` parameter is the authorization code to exchange for tokens.
    """
    # Handle error from Google
    if error:
        telegram_chat_id = _pending_oauth.pop(state, None)
        if telegram_chat_id:
            await bot_client.send_message(
                chat_id=telegram_chat_id,
                text=f"❌ Google authorization failed: {error}\n\nPlease try /connectcalendar again.",
            )
        return HTMLResponse(
            content=ERROR_HTML.format(error=f"Google returned an error: {error}"),
            status_code=400,
        )

    # Validate state
    telegram_chat_id = _pending_oauth.pop(state, None)
    if not telegram_chat_id:
        logger.warning("OAuth callback with unknown state: %s", state)
        return HTMLResponse(
            content=ERROR_HTML.format(error="Invalid state parameter. Please try /connectcalendar again."),
            status_code=400,
        )

    if not code:
        return HTMLResponse(
            content=ERROR_HTML.format(error="No authorization code received."),
            status_code=400,
        )

    try:
        # Exchange code for tokens
        token_data = google_calendar.exchange_code(code, state)

        # Find the user by telegram_chat_id and store tokens
        async for session in get_session():
            user_service = UserService(session)
            user = await user_service.get_by_telegram_id(telegram_chat_id)
            if user:
                await user_service.update_preferences(
                    user.id, {"google_calendar_tokens": token_data}
                )
                # Also update in-memory cache
                update_user_preferences(str(user.id), {"google_calendar_tokens": token_data})

        # Notify user on Telegram
        await bot_client.send_message(
            chat_id=telegram_chat_id,
            text="✅ **Google connected successfully!** 🎉\n\n"
                 "Now you can use:\n\n"
                 "📅 Calendar:\n"
                 "• \"Create an event tomorrow at 3pm\"\n"
                 "• \"What's on my calendar?\"\n\n"
                 "📧 Email:\n"
                 "• \"Send an email to ...\"\n"
                 "• \"Check my inbox\"\n\n"
                 "Both Calendar and Gmail are now connected to your **real Google account**!",
        )

        return HTMLResponse(content=SUCCESS_HTML, status_code=200)

    except Exception as e:
        logger.error("OAuth callback failed: %s", e)
        await bot_client.send_message(
            chat_id=telegram_chat_id,
            text=f"❌ Failed to connect Google Calendar: {e}\n\nPlease try /connectcalendar again.",
        )
        return HTMLResponse(
            content=ERROR_HTML.format(error=str(e)),
            status_code=500,
        )