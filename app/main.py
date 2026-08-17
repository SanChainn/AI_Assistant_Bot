"""
FastAPI application factory.

This is the entry point for the application. The factory pattern ensures
that test environments can create isolated instances of the app.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import router as api_v1_router
from app.bot.client import bot_client
from app.core.config import settings
from app.core.database import close_db, init_db
from app.core.logging import logger, setup_logging
from app.core.redis import close_redis
from app.tools.loader import init_tools


async def setup_telegram_webhook() -> None:
    """
    Register the Telegram webhook on startup when WEBHOOK_URL is configured.

    In production (webhook mode) this tells Telegram where to deliver updates.
    In development (polling mode) WEBHOOK_URL is left empty and run_dev.py
    polls getUpdates instead.
    """
    if not settings.WEBHOOK_URL:
        logger.info("WEBHOOK_URL not set — skipping webhook registration (polling mode)")
        return

    webhook_url = settings.WEBHOOK_URL.rstrip("/")
    full_url = f"{webhook_url}/api/v1/telegram/webhook"
    result = await bot_client.set_webhook(full_url)

    if result.get("ok"):
        logger.info("Telegram webhook registered: %s", full_url)
    else:
        logger.error(
            "Failed to register Telegram webhook: %s — check WEBHOOK_URL "
            "(must be HTTPS on port 443/80/88/8443) and the bot token",
            result.get("description", result),
        )


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan managing startup and shutdown.

    Startup:
        - Configure logging
        - Initialize tools
        - Initialize database connection pool
        - Create missing tables (idempotent; replace with Alembic migrations
          once they are added to the project)
        - Register the Telegram webhook (production/webhook mode only)
    Shutdown:
        - Close the Telegram bot HTTP client
        - Close database connections
        - Close Redis connections
    """
    setup_logging()
    init_tools()
    await init_db()
    await setup_telegram_webhook()
    yield
    await bot_client.close()
    await close_db()
    await close_redis()


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title=settings.APP_NAME,
        version="0.5.0",
        lifespan=lifespan,
    )

    # CORS middleware — restricted in production, permissive in dev
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "http://localhost:8080"] if not settings.APP_DEBUG else ["*"],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["Authorization", "Content-Type"],
    )

    # Register API routers
    app.include_router(api_v1_router)

    return app


app = create_app()