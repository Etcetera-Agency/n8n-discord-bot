"""Async Google Calendar connector used to replace n8n calendar nodes.

Pseudocode from Task02_CalendarConnector.md::

    def base_headers():
        token = os.environ["CALENDAR_TOKEN"]
        return {"Authorization": f"Bearer {token}"}

    CALENDAR_ID = os.environ["CALENDAR_ID"]
    CALENDAR_URL = f"https://www.googleapis.com/calendar/v3/calendars/{CALENDAR_ID}/events"

    async def create_event(summary, start, end):
        payload = {"summary": summary, "start": start, "end": end}
        async with aiohttp.post(CALENDAR_URL, headers=base_headers(), json=payload) as resp:
            data = await resp.json()
            if resp.status != 200:
                return {"status": "error", "message": data.get("error")}
            return {"status": "ok", "event_id": data["id"]}

The implementation below follows this design but derives the OAuth token
from a base64-encoded service account stored in the
``GOOGLE_SERVICE_ACCOUNT_B64`` environment variable. Helpers are provided
for creating day-off and vacation events, and configuration values are
read from ``config.Config`` or environment variables.
"""

from __future__ import annotations

import base64
import json
import os
from typing import Any, Dict, Optional

import aiohttp
from google.auth.transport.requests import Request
from google.oauth2 import service_account

from config import Config


class CalendarError(Exception):
    """Raised when the Calendar API cannot be reached or misconfigured."""


_credentials: service_account.Credentials | None = None


def _get_credentials() -> service_account.Credentials:
    """Load service account credentials from base64 env variable."""

    global _credentials
    if _credentials is None:
        b64 = os.environ.get(
            "GOOGLE_SERVICE_ACCOUNT_B64", Config.GOOGLE_SERVICE_ACCOUNT_B64
        )
        if not b64:
            raise CalendarError("GOOGLE_SERVICE_ACCOUNT_B64 is not configured")
        raw = base64.b64decode(b64).decode("utf-8")
        info = json.loads(raw)
        info["private_key"] = info["private_key"].replace("\\n", "\n")
        _credentials = service_account.Credentials.from_service_account_info(
            info, scopes=["https://www.googleapis.com/auth/calendar"]
        )
    return _credentials


def base_headers() -> Dict[str, str]:
    """Return headers required for all Calendar API requests."""

    creds = _get_credentials()
    creds.refresh(Request())
    return {"Authorization": f"Bearer {creds.token}"}


class CalendarConnector:
    """Asynchronous wrapper around the Google Calendar REST API."""

    def __init__(self, session: Optional[aiohttp.ClientSession] = None) -> None:
        self.session = session

    async def _get_session(self) -> aiohttp.ClientSession:
        if self.session is None or getattr(self.session, "closed", False):
            self.session = aiohttp.ClientSession()
        return self.session

    async def close(self) -> None:
        if self.session and not getattr(self.session, "closed", False):
            await self.session.close()

    async def _create_event(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        session = await self._get_session()
        calendar_id = os.environ.get("CALENDAR_ID", Config.CALENDAR_ID)
        if not calendar_id:
            raise CalendarError("CALENDAR_ID is not configured")
        url = f"https://www.googleapis.com/calendar/v3/calendars/{calendar_id}/events"
        async with session.post(url, headers=base_headers(), json=payload) as resp:
            data = await resp.json()
            if resp.status != 200:
                return {
                    "status": "error",
                    "message": data.get("error", "calendar unreachable"),
                }
            return {"status": "ok", "event_id": data.get("id", "")}

    async def create_day_off_event(self, user_name: str, date: str) -> Dict[str, Any]:
        """Create an all-day day-off event for the given user."""

        payload = {
            "summary": f"Day-off: {user_name}",
            "start": {"date": date},
            "end": {"date": date},
        }
        return await self._create_event(payload)

    async def create_vacation_event(
        self, user_name: str, start_date: str, end_date: str, time_zone: str
    ) -> Dict[str, Any]:
        """Create a vacation event spanning the provided date range."""

        payload = {
            "summary": f"Vacation: {user_name}",
            "start": {"dateTime": f"{start_date}T00:00:00", "timeZone": time_zone},
            "end": {"dateTime": f"{end_date}T23:59:59", "timeZone": time_zone},
        }
        return await self._create_event(payload)
