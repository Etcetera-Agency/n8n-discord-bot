"""Async Notion connector used to replace n8n Notion nodes.

Pseudocode from Task01_NotionConnector.md::

    def base_headers():
        token = os.environ["NOTION_TOKEN"]
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Notion-Version": "2022-06-28",
        }

    async def query_database(database_id, filter):
        url = f"https://api.notion.com/v1/databases/{database_id}/query"
        async with aiohttp.post(url, headers=base_headers(), json={"filter": filter}) as resp:
            data = await resp.json()
            if resp.status != 200:
                raise NotionError(data)
            return normalize_query(data)

    async def update_page(page_id, properties):
        url = f"https://api.notion.com/v1/pages/{page_id}"
        async with aiohttp.patch(url, headers=base_headers(), json={"properties": properties}) as resp:
            data = await resp.json()
            if resp.status != 200:
                raise NotionError(data)
            return {"status": "ok"}

The implementation below follows this design and adds helpers for the Team
Directory, Workload, and Profile Stats databases. Database IDs are supplied via
environment variables or ``config.Config`` values.
"""

from __future__ import annotations

import os
from typing import Any, Dict, Optional

import aiohttp

from config import Config


class NotionError(Exception):
    """Raised when the Notion API returns a non-successful response."""


def base_headers() -> Dict[str, str]:
    """Return headers required for all Notion API requests."""

    token = os.environ.get("NOTION_TOKEN", Config.NOTION_TOKEN)
    if not token:
        raise NotionError("NOTION_TOKEN is not configured")
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28",
    }


def _extract_property(prop: Dict[str, Any], field_name: str) -> Any:
    """Extract a value from a Notion property block."""

    if not prop:
        return ""
    if "title" in prop:
        return "".join(t.get("plain_text", "") for t in prop["title"])
    if "rich_text" in prop:
        texts = prop["rich_text"]
        if field_name == "to_do":
            for t in texts:
                if t.get("href"):
                    return t["href"].strip()
                text = t.get("plain_text", "").strip()
                if text.startswith("http"):
                    return text
        return "".join(t.get("plain_text", "") for t in texts)
    if "number" in prop:
        return prop.get("number") or 0
    return ""


def normalize_query(data: Dict[str, Any], mapping: Dict[str, str]) -> Dict[str, Any]:
    """Normalize Notion query results using a property mapping."""

    results = []
    for item in data.get("results", []):
        props = item.get("properties", {})
        normalized = {
            "id": item.get("id", ""),
            "url": item.get("url", ""),
        }
        for out_name, prop_name in mapping.items():
            normalized[out_name] = _extract_property(props.get(prop_name, {}), out_name)
        results.append(normalized)
    return {"status": "ok", "results": results}


class NotionConnector:
    """Asynchronous wrapper around the Notion REST API."""

    def __init__(self, session: Optional[aiohttp.ClientSession] = None) -> None:
        self.session = session

    async def _get_session(self) -> aiohttp.ClientSession:
        if self.session is None or getattr(self.session, "closed", False):
            self.session = aiohttp.ClientSession()
        return self.session

    async def close(self) -> None:
        if self.session and not getattr(self.session, "closed", False):
            await self.session.close()

    async def query_database(
        self,
        database_id: str,
        filter: Dict[str, Any],
        mapping: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Query a Notion database and return normalized results."""

        session = await self._get_session()
        url = f"https://api.notion.com/v1/databases/{database_id}/query"
        async with session.post(url, headers=base_headers(), json={"filter": filter}) as resp:
            data = await resp.json()
            if resp.status != 200:
                raise NotionError(data)
        return normalize_query(data, mapping or {})

    async def update_page(self, page_id: str, properties: Dict[str, Any]) -> Dict[str, str]:
        """Update properties on a Notion page."""

        session = await self._get_session()
        url = f"https://api.notion.com/v1/pages/{page_id}"
        async with session.patch(url, headers=base_headers(), json={"properties": properties}) as resp:
            data = await resp.json()
            if resp.status != 200:
                raise NotionError(data)
        return {"status": "ok"}

    # --- Helper methods for specific databases ---

    async def find_team_directory_by_channel(self, channel_id: str) -> Dict[str, Any]:
        filter = {
            "property": "Discord channel ID",
            "rich_text": {"contains": channel_id},
        }
        mapping = {
            "name": "Name",
            "discord_id": "Discord ID",
            "channel_id": "Discord channel ID",
            "to_do": "ToDo",
        }
        return await self.query_database(Config.NOTION_TEAM_DIRECTORY_DB_ID, filter, mapping)

    async def update_team_directory_ids(
        self, page_id: str, discord_id: str, channel_id: str
    ) -> Dict[str, str]:
        properties = {
            "Discord ID": {"rich_text": [{"text": {"content": discord_id}}]},
            "Discord channel ID": {"rich_text": [{"text": {"content": channel_id}}]},
        }
        return await self.update_page(page_id, properties)

    async def get_workload_page_by_name(self, name: str) -> Dict[str, Any]:
        filter = {"property": "Name", "title": {"equals": name}}
        mapping = {"name": "Name"}
        return await self.query_database(Config.NOTION_WORKLOAD_DB_ID, filter, mapping)

    async def update_workload_day(
        self, page_id: str, day_field: str, hours: float
    ) -> Dict[str, str]:
        properties = {day_field: {"number": hours}}
        return await self.update_page(page_id, properties)

    async def get_profile_stats_by_name(self, name: str) -> Dict[str, Any]:
        filter = {"property": "Name", "title": {"equals": name}}
        mapping = {"name": "Name", "connects": "Upwork connects"}
        return await self.query_database(Config.NOTION_PROFILE_STATS_DB_ID, filter, mapping)

    async def update_profile_stats_connects(
        self, page_id: str, connects: int
    ) -> Dict[str, str]:
        properties = {"Upwork connects": {"number": connects}}
        return await self.update_page(page_id, properties)

