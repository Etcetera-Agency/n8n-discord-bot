from __future__ import annotations

from typing import Any, Dict

from config import Config, logger
from services.calendar_connector import CalendarConnector
try:  # pragma: no cover - optional dependency
    from services.survey_steps_db import SurveyStepsDB
except Exception:  # pragma: no cover - databases package missing
    SurveyStepsDB = None
from services.date_utils import format_date_ua, is_valid_iso_date

calendar = CalendarConnector()
db_url = getattr(Config, "DATABASE_URL", "")
_steps_db = SurveyStepsDB(db_url) if SurveyStepsDB and db_url else None


async def _mark_step(channel_id: str, step: str) -> None:
    if _steps_db:
        await _steps_db.upsert_step(channel_id, step, True)


async def handle(payload: Dict[str, Any]) -> str:
    """Record day-off dates for the current or next week."""

    try:
        value = (
            payload.get("result", {}).get("value")
            or payload.get("result", {}).get("daysSelected")
        )
        step = payload.get("command")
        if step == "survey":
            step = payload.get("result", {}).get("stepName")
        if value == "Nothing" or not value:
            await _mark_step(payload.get("channelId", ""), step)
            return "Записав! Вихідних нема"
        if isinstance(value, str):
            value = [value]
        author = payload.get("author", "")
        for day in value:
            if not is_valid_iso_date(day):
                logger.error("Invalid day-off date provided: %s", day)
                return f"Некоректна дата: {day}"
            try:
                resp = await calendar.create_day_off_event(author, day)
            except Exception:  # pragma: no cover - defensive
                logger.exception("create_day_off_event failed for %s", day)
                return "Спробуй трохи піздніше. Я тут пораюсь по хаті."
            if resp.get("status") != "ok":
                msg = resp.get("message", "")
                logger.error("Calendar error for %s: %s", day, msg)
                return msg or "Спробуй трохи піздніше. Я тут пораюсь по хаті."
        await _mark_step(payload.get("channelId", ""), step)
        if len(value) == 1:
            return (
                f"Вихідний: {format_date_ua(value[0])} записано.\n"
                "Не забудь попередити клієнтів."
            )
        formatted = ", ".join(format_date_ua(v) for v in value)
        return (
            f"Вихідні: {formatted} записані.\n"
            "Не забудь попередити клієнтів."
        )
    except Exception:  # pragma: no cover - defensive
        logger.exception("Unexpected error in day_off.handle")
        return "Спробуй трохи піздніше. Я тут пораюсь по хаті."
