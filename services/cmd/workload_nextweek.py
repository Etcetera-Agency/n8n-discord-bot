from typing import Any, Dict, Optional, Union
from services.notion_connector import NotionConnector
from config import Config
from services.logging_utils import get_logger

try:
    from services.survey_steps_db import SurveyStepsDB
except Exception:  # pragma: no cover - missing optional dep
    SurveyStepsDB = None

ERROR_MSG = "Спробуй трохи піздніше. Я тут пораюсь по хаті."

_notion = NotionConnector()
_steps: Optional[SurveyStepsDB]
try:
    _steps = SurveyStepsDB(Config.DATABASE_URL)
except Exception:  # pragma: no cover - optional database
    _steps = None


def template(hours: Union[int, float]) -> str:
    """Return message confirming planned hours for next week."""
    return f"Записав! \nЗаплановане навантаження на наступний тиждень: {hours} год."


async def handle(payload: Dict[str, Any]) -> str:
    """Handle the `workload_nextweek` command."""
    log = get_logger()
    try:
        hours = int(payload["result"]["value"])
        log.debug("parsed hours", extra={"hours": hours})
        page_data = await _notion.get_workload_page_by_name(payload["author"])
        results = page_data.get("results", [])
        if not results:
            return ERROR_MSG
        page = results[0]
        await _notion.update_workload_day(page["id"], "Next week plan", hours)
        log.info("workload updated", extra={"page_id": page["id"]})
        if _steps:
            await _steps.upsert_step(payload["channelId"], "workload_nextweek", True)
            log.info("step recorded")
        return template(hours)
    except Exception:
        log.exception("workload_nextweek failed")
        return ERROR_MSG
