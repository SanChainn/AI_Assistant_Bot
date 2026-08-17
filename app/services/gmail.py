"""
Gmail integration service.

Reuses the same Google OAuth2 tokens as Google Calendar (stored in
the user's preferences under "google_calendar_tokens"). Provides
real email sending and inbox listing via the Gmail API.
"""

import base64
from email.mime.text import MIMEText
from typing import Optional

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from app.core.logging import logger
from app.services.google_calendar import _get_credentials


def _get_gmail_service(token_data: dict):
    """
    Build a Gmail API service instance from stored OAuth tokens.

    Args:
        token_data: OAuth tokens from the user's preferences.

    Returns:
        A Gmail service resource, or None if not authenticated.
    """
    creds = _get_credentials(token_data)
    if not creds:
        return None
    return build("gmail", "v1", credentials=creds, cache_discovery=False)


async def send_email(
    token_data: dict,
    to: str,
    subject: str,
    body: str,
) -> dict:
    """
    Send an email via the user's Gmail account.

    Args:
        token_data: OAuth tokens from the user's preferences.
        to: Recipient email address.
        subject: Email subject line.
        body: Email body content (plain text).

    Returns:
        A dict with the sent email's id and thread id.

    Raises:
        Exception: If Gmail is not connected or the API fails.
    """
    service = _get_gmail_service(token_data)
    if not service:
        raise Exception("Gmail not connected. Use /connectcalendar first.")

    message = MIMEText(body)
    message["to"] = to
    message["subject"] = subject

    # Gmail API requires raw base64url-encoded RFC 2822 message
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()

    try:
        sent = (
            service.users()
            .messages()
            .send(userId="me", body={"raw": raw})
            .execute()
        )
        logger.info("Gmail sent to %s: %s (id=%s)", to, subject, sent.get("id"))
        return {
            "id": sent.get("id"),
            "thread_id": sent.get("threadId"),
            "to": to,
            "subject": subject,
        }
    except HttpError as e:
        logger.error("Gmail API error (send): %s", e)
        raise Exception(f"Gmail error: {e}")


async def list_inbox(
    token_data: dict,
    max_results: int = 10,
) -> list[dict]:
    """
    List recent inbox emails from the user's Gmail account.

    Args:
        token_data: OAuth tokens from the user's preferences.
        max_results: Maximum number of emails to return.

    Returns:
        A list of email dicts with from, subject, snippet, and date.

    Raises:
        Exception: If Gmail is not connected or the API fails.
    """
    service = _get_gmail_service(token_data)
    if not service:
        raise Exception("Gmail not connected. Use /connectcalendar first.")

    try:
        # Get list of message IDs from inbox
        results = (
            service.users()
            .messages()
            .list(
                userId="me",
                labelIds=["INBOX"],
                maxResults=min(max_results, 20),
            )
            .execute()
        )
        message_ids = results.get("messages", [])

        if not message_ids:
            return []

        emails = []
        for msg_ref in message_ids:
            msg = (
                service.users()
                .messages()
                .get(
                    userId="me",
                    id=msg_ref["id"],
                    format="metadata",
                    metadataHeaders=["From", "Subject", "Date"],
                )
                .execute()
            )

            headers = {h["name"]: h["value"] for h in msg.get("payload", {}).get("headers", [])}
            emails.append({
                "id": msg.get("id"),
                "from": headers.get("From", "(unknown)"),
                "subject": headers.get("Subject", "(no subject)"),
                "date": headers.get("Date", ""),
                "snippet": msg.get("snippet", ""),
            })

        logger.info("Gmail inbox: %d emails retrieved", len(emails))
        return emails
    except HttpError as e:
        logger.error("Gmail API error (list): %s", e)
        raise Exception(f"Gmail error: {e}")