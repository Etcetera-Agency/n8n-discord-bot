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

The implementation below follows this design and provides helpers for
creating day-off and vacation events. Configuration values are read from
``config.Config`` or environment variables.
"""

from __future__ import annotations

import os
from typing import Any, Dict, Optional

import aiohttp

from config import Config


class CalendarError(Exception):
    """Raised when the Calendar API cannot be reached or misconfigured."""


def base_headers() -> Dict[str, str]:
    """Return headers required for all Calendar API requests."""

    token = os.environ.get("CALENDAR_TOKEN", Config.CALENDAR_TOKEN)
    if not token:
        raise CalendarError("CALENDAR_TOKEN is not configured")
    return {"Authorization": f"Bearer {token}"}


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
