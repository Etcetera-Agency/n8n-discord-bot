from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from typing import Any, Dict, Optional

from config import Config
from services.survey_steps_db import SurveyStepsDB


async def handle(payload: Dict[str, Any], repo: Optional[SurveyStepsDB] = None) -> Dict[str, Any]:
    """Return pending survey steps for the channel or an error message."""
    db = repo or SurveyStepsDB(Config.DATABASE_URL)
    try:
        now = datetime.now(ZoneInfo("Europe/Kyiv"))
        start = (now - timedelta(days=now.weekday())).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        records = await db.fetch_week(payload["channelId"], start)
        steps = [r["step_name"] for r in records if not r["completed"]]
        return {"output": True, "steps": list(dict.fromkeys(steps))}
    except Exception:
        return {
            "output": False,
            "message": "Спробуй трохи піздніше. Я тут пораюсь по хаті.",
        }
    finally:
        if repo is None:
            await db.close()
