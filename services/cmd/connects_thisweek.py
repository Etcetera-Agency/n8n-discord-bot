"""Handler for recording remaining Upwork connects for the week."""

from __future__ import annotations

from typing import Any, Dict

import aiohttp

from config import Config, Strings
from services.notion_connector import NotionConnector, NotionError
from services.logging_utils import get_logger
from services.survey_steps_db import SurveyStepsDB
from services.survey_models import SurveyEvent
from typing import Union
from services.error_utils import handle_exception


ERROR_MESSAGE = Strings.TRY_AGAIN_LATER


async def handle(event: Union[SurveyEvent, Dict[str, Any]]) -> str:
    """Record weekly connects and update optional profile stats."""
    log = get_logger()
    try:
        if isinstance(event, dict):
            connects = int(event.get("result", {}).get("connects") or event.get("result", {}).get("value"))
            author = event.get("author")
            channel_id = event.get("channelId")
        else:
            connects = int(event.result.value)
            author = event.payload.author
            channel_id = event.payload.channelId
        log.debug("parsed connects", extra={"connects": connects})

        # mark survey step as completed using channel id as session id
        db = SurveyStepsDB(Config.DATABASE_URL)
        try:
            await db.upsert_step(channel_id, "connects_thisweek", True)
            log.info("step recorded")
        finally:
            await db.close()

        # post connects count to external database
        url = Config.CONNECTS_URL

        async with aiohttp.ClientSession() as session:
            await session.post(
                url, json={"name": author, "connects": connects}
            )
        log.info("connects posted", extra={"url": url})

        # update profile stats in notion if page exists
        notion = NotionConnector()
        stats = await notion.get_profile_stats_by_name(author)
        results = stats.get("results", []) if isinstance(stats, dict) else []
        if results:
            page_id = results[0].get("id")
            try:
                await notion.update_profile_stats_connects(page_id, connects)
                log.info("notion stats updated", extra={"page_id": page_id})
            except Exception:  # pragma: no cover - best effort
                log.exception("update profile stats failed")
        await notion.close()

        return (
            f"Записав! Upwork connects: залишилось {connects} на цьому тиждні."
        )
    except NotionError as ne:
        return handle_exception(ne)
    except Exception as e:
        return handle_exception(e)
