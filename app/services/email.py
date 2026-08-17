"""
Email service.

Provides email sending and inbox management using an in-memory store
that can be swapped for Gmail API, SMTP, etc.
"""

from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from app.core.logging import logger


class EmailMessage:
    """Represents an email message."""
    def __init__(
        self,
        to: str,
        subject: str,
        body: str,
        from_addr: str = "assistant@ai-personal-assistant.com",
        email_id: Optional[str] = None,
    ):
        self.id = email_id or str(uuid4())
        self.from_addr = from_addr
        self.to = to
        self.subject = subject
        self.body = body
        self.sent_at = datetime.now(timezone.utc).isoformat()


class EmailService:
    """
    Email service for sending and managing emails.

    Currently uses an in-memory store. Will be replaced with
    Gmail API / SMTP integration in production.
    """

    def __init__(self) -> None:
        self._sent: list[EmailMessage] = []
        self._inbox: list[EmailMessage] = []

    async def send_email(
        self,
        to: str,
        subject: str,
        body: str,
    ) -> dict:
        """Send an email."""
        email = EmailMessage(to=to, subject=subject, body=body)
        self._sent.append(email)
        logger.info("Email sent to %s: %s", to, subject)
        return {
            "id": email.id,
            "to": email.to,
            "subject": email.subject,
            "sent_at": email.sent_at,
        }

    async def list_inbox(self, limit: int = 10) -> list[dict]:
        """List inbox messages."""
        inbox = sorted(self._inbox, key=lambda e: e.sent_at, reverse=True)[:limit]
        return [
            {
                "id": e.id,
                "from": e.from_addr,
                "subject": e.subject,
                "body": e.body,
                "received_at": e.sent_at,
            }
            for e in inbox
        ]

    async def list_sent(self, limit: int = 10) -> list[dict]:
        """List sent emails."""
        sent = sorted(self._sent, key=lambda e: e.sent_at, reverse=True)[:limit]
        return [
            {
                "id": e.id,
                "to": e.to,
                "subject": e.subject,
                "sent_at": e.sent_at,
            }
            for e in sent
        ]


# Singleton instance
email_service = EmailService()