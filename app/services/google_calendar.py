"""
Google Calendar integration service.

Provides OAuth2 authentication flow and Google Calendar API operations.
Tokens are stored per-user in the user's preferences JSON field.
"""

import json
import os
import pickle
from datetime import datetime, timedelta, timezone
from typing import Optional
from urllib.parse import urlencode

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from app.core.config import settings
from app.core.logging import logger

# Google API scopes — Calendar (read/write) + Gmail (send + read)
SCOPES = [
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.readonly",
]

# Max results per list request
MAX_RESULTS = 20


def _build_auth_url(state: str = "") -> str:
    """
    Build the Google OAuth2 authorization URL manually.

    We construct the URL directly to avoid PKCE/code_verifier issues.
    Since we're a confidential web client (client_secret stored server-side),
    PKCE is not needed.
    """
    params = {
        "response_type": "code",
        "client_id": settings.GOOGLE_CLIENT_ID,
        "redirect_uri": settings.GOOGLE_REDIRECT_URI,
        "scope": " ".join(SCOPES),
        "access_type": "offline",
        "prompt": "consent",
        "include_granted_scopes": "true",
        "state": state,
    }
    return "https://accounts.google.com/o/oauth2/auth?" + urlencode(params)


def get_auth_url(state: str = "") -> str:
    """Generate the OAuth2 authorization URL for the user."""
    return _build_auth_url(state)


def exchange_code(code: str, state: str = "") -> dict:
    """
    Exchange an OAuth2 authorization code for tokens.

    Uses a direct HTTP POST to Google's token endpoint (confidential
    web client flow, no PKCE needed).
    """
    import httpx

    resp = httpx.post(
        "https://oauth2.googleapis.com/token",
        data={
            "code": code,
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "redirect_uri": settings.GOOGLE_REDIRECT_URI,
            "grant_type": "authorization_code",
        },
        timeout=30.0,
    )
    token_resp = resp.json()

    if "error" in token_resp:
        error_desc = token_resp.get("error_description", token_resp["error"])
        raise Exception(f"Google token exchange failed: {error_desc}")

    token_data = {
        "token": token_resp["access_token"],
        "refresh_token": token_resp.get("refresh_token"),
        "token_uri": "https://oauth2.googleapis.com/token",
        "client_id": settings.GOOGLE_CLIENT_ID,
        "client_secret": settings.GOOGLE_CLIENT_SECRET,
        "scopes": SCOPES,
        "expiry": None,
        "connected": True,
    }

    # Calculate expiry from expires_in
    if "expires_in" in token_resp:
        expiry = datetime.now(timezone.utc) + timedelta(seconds=token_resp["expires_in"])
        token_data["expiry"] = expiry.isoformat()

    logger.info("Google OAuth2 tokens exchanged successfully")
    return token_data


def _get_credentials(token_data: dict) -> Optional[Credentials]:
    """
    Build a Credentials object from stored token data.
    Automatically refreshes if expired.
    """
    if not token_data or not token_data.get("token"):
        return None

    try:
        # Parse expiry from ISO string
        expiry = None
        expiry_str = token_data.get("expiry")
        if expiry_str:
            try:
                expiry = datetime.fromisoformat(expiry_str)
                # Google's Credentials.expired compares with datetime.utcnow()
                # which is naive, so we must strip timezone info to avoid
                # "can't compare offset-naive and offset-aware datetimes"
                if expiry.tzinfo is not None:
                    expiry = expiry.replace(tzinfo=None)
            except (ValueError, TypeError):
                pass

        creds = Credentials(
            token=token_data["token"],
            refresh_token=token_data.get("refresh_token"),
            token_uri=token_data.get("token_uri", "https://oauth2.googleapis.com/token"),
            client_id=token_data.get("client_id"),
            client_secret=token_data.get("client_secret"),
            scopes=token_data.get("scopes", SCOPES),
            expiry=expiry,
        )

        # Refresh if expired
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            logger.info("Google token refreshed")

        return creds
    except Exception as e:
        logger.error("Failed to build Google credentials: %s", e)
        return None


def _get_service(token_data: dict):
    """Build a Google Calendar API service instance."""
    creds = _get_credentials(token_data)
    if not creds:
        return None
    return build("calendar", "v3", credentials=creds)


async def create_event(
    token_data: dict,
    summary: str,
    start_time: str,
    end_time: str,
    description: str = "",
) -> dict:
    """Create an event on the user's Google Calendar."""
    service = _get_service(token_data)
    if not service:
        raise Exception("Google Calendar not connected. Use /connect_calendar first.")

    event_body = {
        "summary": summary,
        "description": description,
        "start": {"dateTime": start_time, "timeZone": "UTC"},
        "end": {"dateTime": end_time, "timeZone": "UTC"},
    }

    try:
        event = (
            service.events()
            .insert(calendarId="primary", body=event_body)
            .execute()
        )
        logger.info("Google Calendar event created: %s (%s)", summary, event.get("id"))
        return {
            "id": event.get("id"),
            "title": event.get("summary"),
            "start_time": event.get("start", {}).get("dateTime"),
            "end_time": event.get("end", {}).get("dateTime"),
            "description": event.get("description", ""),
            "html_link": event.get("htmlLink"),
        }
    except HttpError as e:
        logger.error("Google Calendar API error: %s", e)
        raise Exception(f"Google Calendar error: {e}")


async def list_events(
    token_data: dict,
    max_results: int = 10,
) -> list[dict]:
    """List upcoming events from the user's Google Calendar."""
    service = _get_service(token_data)
    if not service:
        raise Exception("Google Calendar not connected. Use /connect_calendar first.")

    now = datetime.now(timezone.utc).isoformat()

    try:
        events_result = (
            service.events()
            .list(
                calendarId="primary",
                timeMin=now,
                maxResults=min(max_results, MAX_RESULTS),
                singleEvents=True,
                orderBy="startTime",
            )
            .execute()
        )
        events = events_result.get("items", [])

        result = []
        for event in events:
            start = event["start"].get("dateTime", event["start"].get("date"))
            result.append({
                "id": event.get("id"),
                "title": event.get("summary", "(No title)"),
                "start_time": start,
                "description": event.get("description", ""),
                "html_link": event.get("htmlLink"),
            })

        logger.info("Google Calendar: %d upcoming events found", len(result))
        return result
    except HttpError as e:
        logger.error("Google Calendar API error: %s", e)
        raise Exception(f"Google Calendar error: {e}")


async def delete_event(
    token_data: dict,
    event_id: str,
) -> bool:
    """Delete an event from the user's Google Calendar."""
    service = _get_service(token_data)
    if not service:
        raise Exception("Google Calendar not connected. Use /connect_calendar first.")

    try:
        service.events().delete(calendarId="primary", eventId=event_id).execute()
        logger.info("Google Calendar event deleted: %s", event_id)
        return True
    except HttpError as e:
        logger.error("Google Calendar API error: %s", e)
        raise Exception(f"Google Calendar error: {e}")