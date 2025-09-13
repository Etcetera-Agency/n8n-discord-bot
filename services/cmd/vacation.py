"""Vacation command handler."""

from __future__ import annotations

from datetime import datetime

from config import Config
from services.calendar_connector import CalendarConnector
from services.logging_utils import get_logger
from services.error_utils import handle_exception
from services.survey_steps_db import SurveyStepsDB
from services.survey_models import SurveyEvent

# Reusable calendar connector instance
calendar = CalendarConnector()

WEEKDAYS = [
    "Понеділок",
    "Вівторок",
    "Середа",
    "Четвер",
    "П'ятниця",
    "Субота",
    "Неділя",
]

MONTHS = [
    "Січень",
    "Лютий",
    "Березень",
    "Квітень",
    "Травень",
    "Червень",
    "Липень",
    "Серпень",
    "Вересень",
    "Жовтень",
    "Листопад",
    "Грудень",
]


def _fmt(date_str: str) -> str:
    dt = datetime.fromisoformat(date_str)
    weekday = WEEKDAYS[dt.weekday()]
    month = MONTHS[dt.month - 1]
    return f"{weekday} {dt.day:02d} {month} {dt.year}"


async def handle(event: SurveyEvent) -> str:
    """Handle the vacation command."""
    log = get_logger()
    try:
        result = event.result.value or {}
        start_raw = result["start_date"]
        end_raw = result["end_date"]
        author = event.payload.author or ""
        channel_id = str(event.payload.channelId)
        log.debug("dates parsed", extra={"start": start_raw, "end": end_raw})

        # Payload dates may include a time component, but the calendar
        # connector expects bare ``YYYY-MM-DD`` strings.
        start = start_raw.split("T")[0]
        end = end_raw.split("T")[0]

        resp = await calendar.create_vacation_event(
            author, start, end, "Europe/Kyiv"
        )
        if resp.get("status") != "ok":
            raise Exception("calendar error")
        log.info("calendar event created", extra={"event_id": resp.get("event_id")})

        db = SurveyStepsDB(getattr(Config, "DATABASE_URL", ""))
        try:
            await db.upsert_step(
                channel_id, "vacation", True
            )
            log.info("step recorded")
        finally:
            await db.close()

        return f"Записав! Відпустка: {_fmt(start_raw)}—{_fmt(end_raw)}."
    except Exception as e:
        return handle_exception(e)
