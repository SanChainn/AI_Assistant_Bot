"""
Celery worker configuration.

Celery handles background tasks such as:
- Sending Telegram messages asynchronously
- Running long LLM inference jobs
- Processing file uploads for RAG
- Periodic tasks (e.g., daily summaries)
"""

import asyncio
import json
from datetime import timedelta

from celery import Celery
from celery.schedules import crontab

from app.core.config import settings

celery_app = Celery(
    "assistant",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    beat_schedule={
        "cleanup-old-chats": {
            "task": "cleanup_old_chats",
            "schedule": timedelta(hours=24),
        },
    },
)


@celery_app.task(name="send_telegram_message")
def send_telegram_message(chat_id: int, text: str) -> dict:
    """Send a Telegram message asynchronously."""
    from app.bot.client import bot_client

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    result = loop.run_until_complete(bot_client.send_message(chat_id=chat_id, text=text))
    loop.close()
    return result


@celery_app.task(name="process_document_async")
def process_document_async(content: str, metadata: dict) -> dict:
    """Process and index a document in the background."""
    from app.services.rag import rag_service

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    doc_id = loop.run_until_complete(
        rag_service.index_document(content=content, metadata=metadata)
    )
    loop.close()
    return {"doc_id": doc_id, "status": "indexed"}


@celery_app.task(name="cleanup_old_chats")
def cleanup_old_chats() -> str:
    """
    Periodic task: archives inactive chats.
    Runs daily via Celery Beat.
    """
    from datetime import datetime, timezone, timedelta
    from app.core.database import AsyncSessionLocal
    from app.repositories.chat import ChatRepository

    async def _cleanup():
        async with AsyncSessionLocal() as session:
            repo = ChatRepository(session)
            from sqlalchemy import select, update
            from app.models.chat import Chat

            cutoff = datetime.now(timezone.utc) - timedelta(days=30)
            stmt = (
                update(Chat)
                .where(Chat.status == "active", Chat.updated_at < cutoff)
                .values(status="archived")
            )
            await session.execute(stmt)
            await session.commit()

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(_cleanup())
    loop.close()
    return "Old chats archived"