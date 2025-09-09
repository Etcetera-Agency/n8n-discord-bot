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

try:  # pragma: no cover - optional dependency
    from services.survey_steps_db import SurveyStepsDB
except Exception:  # pragma: no cover - missing databases package
    SurveyStepsDB = None  # type: ignore


_notio = NotionConnector()
_steps_db: Optional[SurveyStepsDB]
db_url = getattr(Config, "DATABASE_URL", "")
if SurveyStepsDB and db_url:
    _steps_db = SurveyStepsDB(db_url)
else:  # pragma: no cover - executed only when DB is unavailable
    _steps_db = None

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


async def handle(payload: Dict[str, Any]) -> str:
    """Handle the ``workload_today`` command."""

    try:
        hours = int(payload["result"]["value"])  # 0 is valid
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
            return "Спробуй трохи піздніше. Я тут пораюсь по хаті."
        page = results[0]
        page_id = page.get("id", "")
        capacity = int(page.get("capacity", 0))
        fact = int(
            sum(float(page.get(f"fact_{i}", 0)) for i in range(idx + 1))
        )

        await _notio.update_workload_day(page_id, plan_field, hours)

        if _steps_db:
            await _steps_db.upsert_step(
                str(payload.get("channelId")), "workload_today", True
            )

        day_acc = DAY_ACC[idx]
        day_gen = DAY_GEN[idx]
        return (
            "Записав! \n"
            f"Заплановане навантаження у {day_acc}: {hours} год. \n"
            f"В щоденнику з понеділка до {day_gen}: {fact} год.\n"
            f"Капасіті на цей тиждень: {capacity} год."
        )
    except (NotionError, KeyError, ValueError, TypeError, IndexError):
        return "Спробуй трохи піздніше. Я тут пораюсь по хаті."
