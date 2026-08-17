"""
Email tools for the AI assistant.

Allows the LLM to send emails and manage the inbox.
Uses Gmail API when Google is connected, falls back to in-memory storage.
"""

from typing import Optional

from app.services import gmail as gmail_service
from app.services.email import email_service
from app.tools.base import BaseTool, get_user_preferences


def _get_token_data(user_id: Optional[str] = None) -> Optional[dict]:
    """
    Get Google OAuth tokens from the user's preferences.

    Args:
        user_id: The current user's ID. If None, returns None.

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


class SendEmailTool(BaseTool):
    """Tool to send an email."""

    @property
    def name(self) -> str:
        return "send_email"

    @property
    def description(self) -> str:
        return "Send an email to a recipient with a subject and body. Uses the user's connected Gmail account. If Gmail is not connected, uses a local simulation. Always use this tool when the user asks to send an email."

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "to": {"type": "string", "description": "Recipient email address"},
                "subject": {"type": "string", "description": "Email subject"},
                "body": {"type": "string", "description": "Email body content"},
            },
            "required": ["to", "subject", "body"],
        }

    async def execute(self, to: str, subject: str, body: str, **kwargs) -> str:
        user_id = kwargs.get("user_id")
        token_data = _get_token_data(user_id)

        # Try Gmail API first
        if token_data:
            try:
                result = await gmail_service.send_email(token_data, to, subject, body)
                return f"Email sent via Gmail to {result['to']} with subject '{result['subject']}' (ID: {result['id']})"
            except Exception as e:
                return f"Gmail error: {e}"

        # Fallback to in-memory
        result = await email_service.send_email(to, subject, body)
        return f"Email sent to {result['to']} with subject '{result['subject']}' (ID: {result['id']})"


class ListInboxTool(BaseTool):
    """Tool to list inbox emails."""

    @property
    def name(self) -> str:
        return "list_inbox"

    @property
    def description(self) -> str:
        return "List recent emails from the user's connected Gmail inbox. If Gmail is not connected, checks the local inbox. Always use this tool when the user asks to check their inbox or read emails."

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "description": "Number of emails to return (default 10)"},
            },
            "required": [],
        }

    async def execute(self, limit: int = 10, **kwargs) -> str:
        user_id = kwargs.get("user_id")
        token_data = _get_token_data(user_id)

        # Try Gmail API first
        if token_data:
            try:
                emails = await gmail_service.list_inbox(token_data, limit)
                if not emails:
                    return "No emails in Gmail inbox."
                lines = [
                    f"- From: {e['from']}, Subject: {e['subject']}, Date: {e.get('date', '')}"
                    for e in emails
                ]
                return "Gmail Inbox:\n" + "\n".join(lines)
            except Exception as e:
                return f"Gmail error: {e}"

        # Fallback to in-memory
        emails = await email_service.list_inbox(limit)
        if not emails:
            return "No emails in inbox."
        lines = [f"- From: {e['from']}, Subject: {e['subject']}" for e in emails]
        return "Inbox:\n" + "\n".join(lines)