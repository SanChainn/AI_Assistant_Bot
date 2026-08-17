"""
Calendar service.

Provides calendar event management using an in-memory store
that can be swapped for Google Calendar API, CalDAV, etc.
"""

from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4

from app.core.logging import logger


class CalendarEvent:
    """Represents a calendar event."""
    def __init__(
        self,
        title: str,
        start_time: str,
        end_time: str,
        description: str = "",
        event_id: Optional[str] = None,
    ):
        self.id = event_id or str(uuid4())
        self.title = title
        self.start_time = start_time
        self.end_time = end_time
        self.description = description
        self.created_at = datetime.now(timezone.utc).isoformat()


class CalendarService:
    """
    Calendar service for managing events.

    Currently uses an in-memory store. Will be replaced with
    Google Calendar API integration in production.
    """

    def __init__(self) -> None:
        self._events: list[CalendarEvent] = []

    async def create_event(
        self,
        title: str,
        start_time: str,
        end_time: str,
        description: str = "",
    ) -> dict:
        """Create a new calendar event."""
        event = CalendarEvent(
            title=title,
            start_time=start_time,
            end_time=end_time,
            description=description,
        )
        self._events.append(event)
        logger.info("Calendar event created: %s (%s)", title, start_time)
        return {
            "id": event.id,
            "title": event.title,
            "start_time": event.start_time,
            "end_time": event.end_time,
            "description": event.description,
        }

    async def list_events(self, limit: int = 10) -> list[dict]:
        """List upcoming events."""
        events = sorted(self._events, key=lambda e: e.start_time)[:limit]
        return [
            {
                "id": e.id,
                "title": e.title,
                "start_time": e.start_time,
                "end_time": e.end_time,
                "description": e.description,
            }
            for e in events
        ]

    async def delete_event(self, event_id: str) -> bool:
        """Delete an event by ID."""
        initial_len = len(self._events)
        self._events = [e for e in self._events if e.id != event_id]
        return len(self._events) < initial_len


# Singleton instance
calendar_service = CalendarService()