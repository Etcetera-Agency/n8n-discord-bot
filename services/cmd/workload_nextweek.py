from typing import Optional, Union
from services.notion_connector import NotionConnector, NotionError
from config import Config, Strings
from services.logging_utils import get_logger
from services.survey_steps_db import SurveyStepsDB
from services.survey_models import SurveyEvent
from services.error_utils import handle_exception

ERROR_MSG = Strings.TRY_AGAIN_LATER

_notion = NotionConnector()
_steps: Optional[SurveyStepsDB] = None


def _ensure_db() -> SurveyStepsDB:
    global _steps
    if _steps is None:
        db_url = getattr(Config, "DATABASE_URL", "")
        if not db_url:
            raise RuntimeError("DATABASE_URL not configured")
        _steps = SurveyStepsDB(db_url)
    return _steps


def template(hours: Union[int, float]) -> str:
    """Return message confirming planned hours for next week."""
    return f"Записав! \nЗаплановане навантаження на наступний тиждень: {hours} год."


async def handle(event: SurveyEvent) -> str:
    """Handle the `workload_nextweek` command."""
    log = get_logger()
    try:
        hours_raw = event.result.value
        author = event.payload.author
        channel_id = event.payload.channelId
        hours = int(hours_raw)
        log.debug("parsed hours", extra={"hours": hours})
        page_data = await _notion.get_workload_page_by_name(author)
        results = page_data.get("results", [])
        if not results:
            return ERROR_MSG
        page = results[0]
        await _notion.update_workload_day(page["id"], "Next week plan", hours)
        log.info("workload updated", extra={"page_id": page["id"]})
        db = _ensure_db()
        await db.upsert_step(channel_id, "workload_nextweek", True)
        log.info("step recorded")
        return template(hours)
    except NotionError as ne:
        return handle_exception(ne)
    except Exception as e:
        return handle_exception(e)
