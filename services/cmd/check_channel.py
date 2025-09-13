from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from typing import Any, Dict, Optional

from config import Config
from services.survey_steps_db import SurveyStepsDB
from services.logging_utils import get_logger
from services.error_utils import handle_exception

# Some test environments stub Config without a DATABASE_URL; ensure the
# attribute exists so handler setup doesn't raise AttributeError before we can
# patch it during tests.
if not hasattr(Config, "DATABASE_URL"):
    Config.DATABASE_URL = ""


async def handle(payload: Dict[str, Any], repo: Optional[SurveyStepsDB] = None) -> Dict[str, Any]:
    """Return pending survey steps for the channel or an error message."""
    log = get_logger()
    try:
        db = repo
        if db is None:
            db_url = getattr(Config, "DATABASE_URL", "")
            if not db_url:
                raise RuntimeError("DATABASE_URL not configured")
            db = SurveyStepsDB(db_url)
        now = datetime.now(ZoneInfo("Europe/Kyiv"))
        start = (now - timedelta(days=now.weekday())).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        records = await db.fetch_week(payload["channelId"], start)
        steps = [r["step_name"] for r in records if not r["completed"]]
        log.info("pending steps", extra={"steps": steps})
        return {"output": True, "steps": list(dict.fromkeys(steps))}
    except Exception as e:
        msg = handle_exception(e)
        return {"output": False, "message": msg}
    finally:
        if repo is None and db:
            try:
                await db.close()
            except Exception:  # pragma: no cover - defensive cleanup
                pass
