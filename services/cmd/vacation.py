"""Vacation command handler."""

from __future__ import annotations

from typing import Any, Dict, Optional
from datetime import datetime

from services.calendar_connector import CalendarConnector

# Optional survey step tracker; tests may monkeypatch this.
survey_db: Optional[Any] = None

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

        if survey_db and payload.get("command") == "survey":
            await survey_db.upsert_step(payload.get("userId", ""), "vacation", True)

        return f"Записав! Відпустка: {_fmt(start)}—{_fmt(end)}."
    except Exception:
        return "Спробуй трохи піздніше. Я тут пораюсь по хаті."
