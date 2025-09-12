from __future__ import annotations

from typing import Any, Dict

from config import Config
from services.calendar_connector import CalendarConnector
from services.logging_utils import get_logger
from services.survey_steps_db import SurveyStepsDB
from services.date_utils import format_date_ua, is_valid_iso_date

calendar = CalendarConnector()
_steps_db: SurveyStepsDB | None = None


def _ensure_db() -> SurveyStepsDB:
    """Return a SurveyStepsDB instance using the configured DATABASE_URL."""
    global _steps_db
    if _steps_db is None:
        db_url = getattr(Config, "DATABASE_URL", "")
        if not db_url:
            raise RuntimeError("DATABASE_URL not configured")
        _steps_db = SurveyStepsDB(db_url)
    return _steps_db


async def _mark_step(channel_id: str, step: str) -> None:
    db = _ensure_db()
    await db.upsert_step(channel_id, step, True)


async def handle(payload: Dict[str, Any]) -> str:
    """Record day-off dates for the current or next week."""

    log = get_logger("day_off", payload)
    log.info("start")
    try:
        value = (
            payload.get("result", {}).get("value")
            or payload.get("result", {}).get("daysSelected")
        )
        if isinstance(value, dict) and "values" in value:
            value = value.get("values")
        step = payload.get("command")
        if step == "survey":
            step = payload.get("result", {}).get("stepName")
        if (
            value == "Nothing"
            or value == ["Nothing"]
            or not value
        ):
            await _mark_step(payload.get("channelId", ""), step)
            log.info("done", extra={"output": "Записав! Вихідних нема"})
            return "Записав! Вихідних нема"
        if isinstance(value, str):
            value = [value]
        author = payload.get("author", "")
        for day in value:
            if not is_valid_iso_date(day):
                log.error("Invalid day-off date provided", extra={"day": day})
                return f"Некоректна дата: {day}"
            try:
                resp = await calendar.create_day_off_event(author, day)
            except Exception:  # pragma: no cover - defensive
                log.exception("create_day_off_event failed", extra={"day": day})
                return "Спробуй трохи піздніше. Я тут пораюсь по хаті."
            if resp.get("status") != "ok":
                msg = resp.get("message", "")
                log.error("Calendar error", extra={"day": day, "error": msg})
                return msg or "Спробуй трохи піздніше. Я тут пораюсь по хаті."
        await _mark_step(payload.get("channelId", ""), step)
        if len(value) == 1:
            result = (
                f"Вихідний: {format_date_ua(value[0])} записано.\n"
                "Не забудь попередити клієнтів.\n"
            )
        else:
            formatted = ", ".join(format_date_ua(v) for v in value)
            result = (
                f"Вихідні: {formatted} записані.\n"
                "Не забудь попередити клієнтів.\n"
            )
        log.info("done", extra={"output": result})
        return result
    except Exception:  # pragma: no cover - defensive
        log.exception("failed")
        return "Спробуй трохи піздніше. Я тут пораюсь по хаті."
