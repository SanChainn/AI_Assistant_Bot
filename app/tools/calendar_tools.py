"""
Calendar tools for the AI assistant.

Allows the LLM to create, list, and manage calendar events.
Uses Google Calendar when connected, falls back to in-memory storage.
"""

import json
from typing import Optional

from app.services.calendar import calendar_service
from app.services import google_calendar
from app.tools.base import BaseTool, get_user_preferences, update_user_preferences


def _get_token_data(user_id: Optional[str] = None) -> Optional[dict]:
    """
    Get Google Calendar OAuth tokens from the user's preferences.
    
    Args:
        user_id: The current user's ID. If None, uses in-memory fallback.
    
    Returns:
        Token data dict if connected, None otherwise.
    """
    if not user_id:
        return None
    prefs = get_user_preferences(user_id)
    if not prefs:
        return None
    token_data = prefs.get("google_calendar_tokens")
    if token_data and token_data.get("connected"):
        return token_data
    return None


class CreateEventTool(BaseTool):
    """Tool to create a calendar event."""

    @property
    def name(self) -> str:
        return "create_calendar_event"

    @property
    def description(self) -> str:
        return "Create a new calendar event with a title, start time, end time, and optional description. Uses the user's connected Google Calendar. If Google Calendar is not connected, falls back to a local calendar."

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Event title"},
                "start_time": {"type": "string", "description": "Start time (ISO 8601 format, e.g. 2024-12-25T14:00:00Z)"},
                "end_time": {"type": "string", "description": "End time (ISO 8601 format)"},
                "description": {"type": "string", "description": "Event description (optional)"},
            },
            "required": ["title", "start_time", "end_time"],
        }

    async def execute(self, title: str, start_time: str, end_time: str, description: str = "", user_id: Optional[str] = None) -> str:
        # Try Google Calendar first
        token_data = _get_token_data(user_id)
        if token_data:
            try:
                result = await google_calendar.create_event(
                    token_data, title, start_time, end_time, description
                )
                link = result.get("html_link", "")
                msg = f"Event created on Google Calendar: {result['title']} at {result['start_time']}"
                if link:
                    msg += f"\nLink: {link}"
                return msg
            except Exception as e:
                return f"Google Calendar error: {e}"

        # Fallback to in-memory
        result = await calendar_service.create_event(title, start_time, end_time, description)
        return f"Event created (local): {result['title']} at {result['start_time']} (ID: {result['id']})"


class ListEventsTool(BaseTool):
    """Tool to list calendar events."""

    @property
    def name(self) -> str:
        return "list_calendar_events"

    @property
    def description(self) -> str:
        return "List upcoming calendar events from the user's connected Google Calendar. If Google Calendar is not connected, lists events from the local calendar. Always use this tool when the user asks about their calendar, schedule, or upcoming events."

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "description": "Number of events to return (default 10)"},
            },
            "required": [],
        }

    async def execute(self, limit: int = 10, user_id: Optional[str] = None) -> str:
        # Try Google Calendar first
        token_data = _get_token_data(user_id)
        if token_data:
            try:
                events = await google_calendar.list_events(token_data, limit)
                if not events:
                    return "No upcoming events on Google Calendar."
                lines = []
                for e in events:
                    link = e.get("html_link", "")
                    line = f"- {e['title']} at {e['start_time']}"
                    if link:
                        line += f" ({link})"
                    lines.append(line)
                return "Upcoming events (Google Calendar):\n" + "\n".join(lines)
            except Exception as e:
                return f"Google Calendar error: {e}"

        # Fallback to in-memory
        events = await calendar_service.list_events(limit)
        if not events:
            return "No upcoming events (local)."
        lines = [f"- {e['title']} at {e['start_time']} (ID: {e['id']})" for e in events]
        return "Upcoming events (local):\n" + "\n".join(lines)
