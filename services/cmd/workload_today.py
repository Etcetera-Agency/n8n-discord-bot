"""Handler for the ``workload_today`` command.

This replaces the n8n workflow step that recorded a user's planned hours for
the current day.  The function reads the desired number of hours from the
payload, writes them to the Notion Workload database and marks the survey step
as completed.  Any failure in the Notion interaction results in a generic
error message being returned.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from config import Config
from services.notion_connector import NotionConnector, NotionError
from services.logging_utils import get_logger
from services.survey_steps_db import SurveyStepsDB


_notio = NotionConnector()
_steps_db: Optional[SurveyStepsDB] = None


def _ensure_db() -> SurveyStepsDB:
    global _steps_db
    if _steps_db is None:
        db_url = getattr(Config, "DATABASE_URL", "")
        if not db_url:
            raise RuntimeError("DATABASE_URL not configured")
        _steps_db = SurveyStepsDB(db_url)
    return _steps_db

# Day name mappings for Ukrainian output and Notion fields
DAY_SHORT = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
DAY_ACC = [
    "понеділок",
    "вівторок",
    "середу",
    "четвер",
    "п'ятницю",
    "суботу",
    "неділю",
]
DAY_GEN = [
    "понеділка",
    "вівторка",
    "середи",
    "четверга",
    "п'ятниці",
    "суботи",
    "неділі",
]

ERROR_MSG = "Спробуй трохи піздніше. Я тут пораюсь по хаті."


async def handle(payload: Dict[str, Any]) -> str:
    """Handle the ``workload_today`` command."""

    log = get_logger()
    try:
        result = payload.get("result", {})
        hours_raw = result.get("value", result.get("workload"))
        hours = int(hours_raw)  # 0 is valid
        log.debug("parsed hours", extra={"hours": hours})
        ts = payload.get("timestamp")
        now = (
            datetime.fromtimestamp(ts, timezone.utc)
            if ts is not None
            else datetime.now(timezone.utc)
        )
        idx = now.weekday()
        plan_field = f"{DAY_SHORT[idx]} Plan"

        filter = {"property": "Name", "title": {"equals": payload["author"]}}
        mapping: Dict[str, str] = {"capacity": "Capacity"}
        for i in range(idx + 1):
            mapping[f"fact_{i}"] = f"{DAY_SHORT[i]} Fact"
        query = await _notio.query_database(
            Config.NOTION_WORKLOAD_DB_ID, filter, mapping
        )
        results = query.get("results", [])
        if not results:
            return ERROR_MSG
        page = results[0]
        page_id = page.get("id", "")
        capacity = int(page.get("capacity", 0))
        fact = int(
            sum(float(page.get(f"fact_{i}", 0)) for i in range(idx + 1))
        )

        await _notio.update_workload_day(page_id, plan_field, hours)
        log.info("workload updated", extra={"page_id": page_id, "field": plan_field})

        db = _ensure_db()
        await db.upsert_step(
            str(payload.get("channelId")), "workload_today", True
        )
        log.info("step recorded")

        day_acc = DAY_ACC[idx]
        day_gen = DAY_GEN[idx]
        return (
            "Записав! \n"
            f"Заплановане навантаження у {day_acc}: {hours} год. \n"
            f"В щоденнику з понеділка до {day_gen}: {fact} год.\n"
            f"Капасіті на цей тиждень: {capacity} год."
        )
    except (NotionError, KeyError, ValueError, TypeError, IndexError):
        log.exception("workload_today failed")
        return ERROR_MSG
