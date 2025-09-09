"""Vacation command handler."""

from __future__ import annotations

from typing import Any, Dict
from datetime import datetime

from config import Config
from services.calendar_connector import CalendarConnector
try:  # pragma: no cover - optional dependency
    from services.survey_steps_db import SurveyStepsDB
except Exception:  # pragma: no cover - missing databases package
    SurveyStepsDB = None  # type: ignore

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
    return f"{weekday} {dt.day:02d} {month}"


async def handle(payload: Dict[str, Any]) -> str:
    """Handle the vacation command."""

    try:
        result = payload.get("result", {})
        start = result["start_date"]
        end = result["end_date"]

        resp = await calendar.create_vacation_event(
            payload.get("author", ""), start, end, "Europe/Kyiv"
        )
        if resp.get("status") != "ok":
            raise Exception("calendar error")

        db_url = getattr(Config, "DATABASE_URL", "")
        if SurveyStepsDB and db_url:
            db = SurveyStepsDB(db_url)
            try:
                await db.upsert_step(str(payload.get("channelId")), "vacation", True)
            finally:
                await db.close()

        return f"Записав! Відпустка: {_fmt(start)}—{_fmt(end)}."
    except Exception:
        return "Спробуй трохи піздніше. Я тут пораюсь по хаті."
