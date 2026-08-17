"""
Development runner — starts the bot in polling mode with SQLite.

No Docker, no PostgreSQL, no ngrok needed.
Just run: python run_dev.py

This uses:
- SQLite instead of PostgreSQL (auto-created)
- Telegram polling instead of webhook (no public URL needed)
- In-memory instead of Redis/Qdrant (graceful fallback)
"""

import asyncio
import os
import sys

# Force SQLite for development
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./assistant.db"
os.environ["APP_DEBUG"] = "true"
os.environ["USE_POLLING"] = "true"

# Disable Redis/Qdrant for dev (graceful fallback)
os.environ["REDIS_HOST"] = ""
os.environ["QDRANT_HOST"] = ""


async def main():
    print("=" * 60)
    print("AI Personal Assistant - Development Mode")
    print("=" * 60)
    print()

    # Import after env vars are set
    from app.core.config import settings
    from app.core.database import init_db, close_db, async_session_factory
    from app.core.logging import setup_logging
    from app.tools.loader import init_tools
    from app.services.telegram import TelegramService

    setup_logging()
    init_tools()

    print(f"Bot Token: {settings.TELEGRAM_BOT_TOKEN[:10]}...{settings.TELEGRAM_BOT_TOKEN[-5:]}")
    print(f"LLM Model: {settings.LLM_MODEL}")
    print(f"Database: SQLite (assistant.db)")
    print()

    # Initialize database
    print("Initializing database...")
    await init_db()
    print("Database ready.")
    print()

    # Start FastAPI web server (for OAuth callbacks) in background
    # If port is already in use, skip gracefully (polling-only mode)
    import socket
    import uvicorn
    from app.main import app

    def _is_port_free(port: int) -> bool:
        """Check if a TCP port is available."""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(("0.0.0.0", port))
                return True
        except OSError:
            return False

    server_task = None
    server = None
    if _is_port_free(settings.PORT):
        config = uvicorn.Config(
            app,
            host=settings.HOST,
            port=settings.PORT,
            log_level="warning",
        )
        server = uvicorn.Server(config)
        server_task = asyncio.create_task(server.serve())
        print(f"Web server started on http://localhost:{settings.PORT}")
        print(f"  OAuth callback: http://localhost:{settings.PORT}/api/v1/auth/google/callback")
    else:
        print(f"WARNING: Port {settings.PORT} is already in use — skipping web server.")
        print("  OAuth callbacks will not work in this session.")
        print("  To fix: close other instances of this bot, then restart.")
    print()

    print("=" * 60)
    print("Bot is running! Send a message to @sanchaintun_bot on Telegram.")
    print("Press Ctrl+C to stop.")
    print("=" * 60)
    print()

    # Polling loop
    offset = 0
    while True:
        try:
            url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/getUpdates"
            import httpx

            async with httpx.AsyncClient(timeout=35.0) as client:
                response = await client.post(
                    url,
                    json={"offset": offset, "timeout": 30},
                )
                data = response.json()

                if data.get("ok"):
                    for update in data.get("result", []):
                        update_id = update.get("update_id", 0)
                        offset = update_id + 1

                        # Process the update
                        try:
                            async with async_session_factory() as session:
                                service = TelegramService(session)
                                result = await service.handle_update(update)
                                await session.commit()
                                if result.get("ok"):
                                    print(f"  Processed update {update_id} - response: {result.get('response_length', 0)} chars")
                                else:
                                    print(f"  Skipped update {update_id}: {result.get('error')}")
                        except Exception as e:
                            print(f"  Error processing update {update_id}: {e}")
                            import traceback
                            traceback.print_exc()

        except KeyboardInterrupt:
            print("\nShutting down...")
            break
        except Exception as e:
            print(f"  Polling error: {e}")
            await asyncio.sleep(5)

    # Stop web server if it was started
    if server and server_task:
        server.should_exit = True
        try:
            await server_task
        except asyncio.CancelledError:
            pass

    await close_db()
    print("Done.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nStopped.")