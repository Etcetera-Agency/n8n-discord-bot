import os
import sys
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Tuple

import pytest
import types
import logging

# Add project and services directories to import path
ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT))
sys.path.append(str(ROOT / "services"))


class DummyConfig:
    NOTION_TEAM_DIRECTORY_DB_ID = ""
    NOTION_TOKEN = ""
    NOTION_WORKLOAD_DB_ID = ""
    NOTION_PROFILE_STATS_DB_ID = ""
    WEBHOOK_AUTH_TOKEN = ""
    SESSION_TTL = 1


sys.modules["config"] = types.SimpleNamespace(
    Config=DummyConfig, logger=logging.getLogger("test"), Strings=object()
)

from notion_connector import NotionConnector
from config import Config


def load_team_directory():
    text = Path(ROOT / "responses").read_text()
    name = re.search(r'plain_text": "([^"]+Lernichenko)"', text).group(1)
    href = re.search(r'https://www.notion.so/[0-9a-f-]+', text).group(0)
    page_id = re.search(r'id": "([0-9a-f-]{36})"', text).group(1)
    return {
        "id": page_id,
        "url": href,
        "properties": {
            "Name": {"title": [{"plain_text": name}]},
            "Discord ID": {"rich_text": []},
            "Discord channel ID": {"rich_text": []},
            "ToDo": {"rich_text": [{"plain_text": "Todo - " + name, "href": href}]},
        },
    }


class MockResponse:
    """Simple mock for aiohttp response."""

    def __init__(self, status: int, data: Dict[str, Any]):
        self.status = status
        self._data = data

    async def json(self) -> Dict[str, Any]:
        return self._data

    async def __aenter__(self) -> "MockResponse":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None


class DummySession:
    """Session that records calls and returns predefined responses."""

    def __init__(self) -> None:
        self.post_calls: List[Tuple[str, Dict[str, str], Dict[str, Any]]] = []
        self.patch_calls: List[Tuple[str, Dict[str, str], Dict[str, Any]]] = []
        self.post_response: MockResponse | None = None
        self.patch_response: MockResponse | None = None
        self.closed = False

    def post(self, url: str, headers: Dict[str, str], json: Dict[str, Any]):
        self.post_calls.append((url, headers, json))
        return self.post_response

    def patch(self, url: str, headers: Dict[str, str], json: Dict[str, Any]):
        self.patch_calls.append((url, headers, json))
        return self.patch_response

    async def close(self) -> None:
        self.closed = True


@pytest.mark.asyncio
async def test_query_database_normalizes(tmp_path):
    log_file = tmp_path / "query_log.txt"
    log_file.write_text("Input: channel_id=1234567890\n")

    os.environ["NOTION_TOKEN"] = "token"
    Config.NOTION_TEAM_DIRECTORY_DB_ID = "TD_DB"

    session = DummySession()
    page = load_team_directory()
    response_data = {"results": [page]}
    session.post_response = MockResponse(200, response_data)

    connector = NotionConnector(session=session)

    result = await connector.find_team_directory_by_channel("1234567890")
    with open(log_file, "a") as f:
        f.write("Step: called find_team_directory_by_channel\n")
        f.write(f"Output: {result}\n")

    assert session.post_calls
    url, headers, payload = session.post_calls[0]
    assert url == "https://api.notion.com/v1/databases/TD_DB/query"
    assert headers["Authorization"] == "Bearer token"
    assert payload["filter"]["rich_text"]["contains"] == "1234567890"
    assert result["results"][0]["name"] == page["properties"]["Name"]["title"][0]["plain_text"]


@pytest.mark.asyncio
async def test_update_page_success(tmp_path):
    log_file = tmp_path / "update_log.txt"
    log_file.write_text("Input: page_id=PAGE_ID, discord_id=321, channel_id=1234567890\n")

    os.environ["NOTION_TOKEN"] = "token"

    session = DummySession()
    session.patch_response = MockResponse(200, load_team_directory())

    connector = NotionConnector(session=session)

    result = await connector.update_team_directory_ids("PAGE_ID", "321", "1234567890")
    with open(log_file, "a") as f:
        f.write("Step: called update_team_directory_ids\n")
        f.write(f"Output: {result}\n")

    assert session.patch_calls
    url, headers, payload = session.patch_calls[0]
    assert url == "https://api.notion.com/v1/pages/PAGE_ID"
    assert headers["Authorization"] == "Bearer token"
    assert payload["properties"]["Discord ID"]["rich_text"][0]["text"]["content"] == "321"
    assert result == {"status": "ok"}

