from typing import Any, Dict, Optional, Union
from services.notion_connector import NotionConnector
from config import Config

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
    try:
        hours = int(payload["result"]["value"])
        page_data = await _notion.get_workload_page_by_name(payload["author"])
        results = page_data.get("results", [])
        if not results:
            raise Exception("User not found in Notion Workload DB")
        page = results[0]
        await _notion.update_workload_day(page["id"], "Next week plan", hours)
        if _steps:
            await _steps.upsert_step(payload["channelId"], "workload_nextweek", True)
        return template(hours)
    except Exception:
        return ERROR_MSG
