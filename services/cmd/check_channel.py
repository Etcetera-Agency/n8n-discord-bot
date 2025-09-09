from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from config import Config
from services.survey_steps_db import SurveyStepsDB


async def handle(payload: Dict[str, Any], repo: Optional[SurveyStepsDB] = None) -> Dict[str, Any] | str:
    """Return pending survey steps for the channel or an error message."""
    try:
        db = repo or SurveyStepsDB(Config.DATABASE_URL)
        now = datetime.utcnow()
        start = (now - timedelta(days=now.weekday())).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        records = await db.fetch_week(payload["channelId"], start)
        steps = [r["step_name"] for r in records if not r["completed"]]
        if repo is None:
            await db.close()
        return {"output": True, "steps": list(dict.fromkeys(steps))}
    except Exception:
        return "Спробуй трохи піздніше. Я тут пораюсь по хаті."
