"""Handler for recording remaining Upwork connects for the week."""

from __future__ import annotations

import os
from typing import Any, Dict

import aiohttp

from config import Config
from services.notion_connector import NotionConnector

try:  # pragma: no cover - optional dependency
    from services.survey_steps_db import SurveyStepsDB
except Exception:  # pragma: no cover - missing databases package
    SurveyStepsDB = None  # type: ignore


ERROR_MESSAGE = "Спробуй трохи піздніше. Я тут пораюсь по хаті."


async def handle(payload: Dict[str, Any]) -> str:
    """Record weekly connects and update optional profile stats."""
    try:
        connects = int(payload["result"]["connects"])

        # mark survey step as completed using channel id as session id
        if SurveyStepsDB and Config.DATABASE_URL:
            db = SurveyStepsDB(Config.DATABASE_URL)
            try:
                await db.upsert_step(payload["channelId"], "connects_thisweek", True)
            finally:
                await db.close()

        # post connects count to external database
        url = os.environ.get(
            "CONNECTS_URL", "https://tech2.etcetera.kiev.ua/set-db-connects"
        )
        async with aiohttp.ClientSession() as session:
            await session.post(
                url, json={"name": payload["author"], "connects": connects}
            )

        # update profile stats in notion if page exists
        notion = NotionConnector()
        stats = await notion.get_profile_stats_by_name(payload["author"])
        results = stats.get("results", []) if isinstance(stats, dict) else []
        if results:
            page_id = results[0].get("id")
            try:
                await notion.update_profile_stats_connects(page_id, connects)
            except Exception:  # pragma: no cover - best effort
                pass
        await notion.close()

        return (
            f"Записав! Upwork connects: залишилось {connects} на цьому тиждні."
        )
    except Exception:
        return ERROR_MESSAGE

