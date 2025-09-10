"""Handler for recording remaining Upwork connects for the week."""

from __future__ import annotations

from typing import Any, Dict

import aiohttp

from config import Config
from services.notion_connector import NotionConnector
from services.logging_utils import get_logger
from services.survey_steps_db import SurveyStepsDB


ERROR_MESSAGE = "Спробуй трохи піздніше. Я тут пораюсь по хаті."


async def handle(payload: Dict[str, Any]) -> str:
    """Record weekly connects and update optional profile stats."""
    log = get_logger()
    try:
        connects = int(payload["result"]["connects"])
        log.debug("parsed connects", extra={"connects": connects})

        # mark survey step as completed using channel id as session id
        db = SurveyStepsDB(Config.DATABASE_URL)
        try:
            await db.upsert_step(payload["channelId"], "connects_thisweek", True)
            log.info("step recorded")
        finally:
            await db.close()

        # post connects count to external database
        url = Config.CONNECTS_URL

        async with aiohttp.ClientSession() as session:
            await session.post(
                url, json={"name": payload["author"], "connects": connects}
            )
        log.info("connects posted", extra={"url": url})

        # update profile stats in notion if page exists
        notion = NotionConnector()
        stats = await notion.get_profile_stats_by_name(payload["author"])
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
    except Exception:
        log.exception("connects_this_week failed")
        return ERROR_MESSAGE

