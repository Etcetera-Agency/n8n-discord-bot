import sys
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Tuple

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT))
sys.path.append(str(ROOT / "services"))

import types
import logging

fake_google = types.ModuleType("google")
auth = types.ModuleType("auth")
transport = types.ModuleType("transport")
requests_mod = types.ModuleType("requests")
requests_mod.Request = object
transport.requests = requests_mod
auth.transport = transport
oauth2 = types.ModuleType("oauth2")
service_account = types.ModuleType("service_account")
service_account.Credentials = object
oauth2.service_account = service_account
fake_google.auth = auth
fake_google.oauth2 = oauth2
sys.modules["google"] = fake_google
sys.modules["google.auth"] = auth
sys.modules["google.auth.transport"] = transport
sys.modules["google.auth.transport.requests"] = requests_mod
sys.modules["google.oauth2"] = oauth2
sys.modules["google.oauth2.service_account"] = service_account

class DummyConfig:
    CALENDAR_ID = ""
    GOOGLE_SERVICE_ACCOUNT_B64 = ""
    NOTION_TEAM_DIRECTORY_DB_ID = ""
    NOTION_TOKEN = ""
    NOTION_WORKLOAD_DB_ID = ""
    NOTION_PROFILE_STATS_DB_ID = ""
    WEBHOOK_AUTH_TOKEN = ""
    SESSION_TTL = 1

config_pkg = types.ModuleType("config")
config_pkg.Config = DummyConfig
config_pkg.logger = logging.getLogger("test")
config_pkg.Strings = object()
config_pkg.WebhookService = object()

config_sub = types.ModuleType("config.config")
config_sub.Config = DummyConfig

sys.modules["config"] = config_pkg
sys.modules["config.config"] = config_sub

import calendar_connector as cc
from calendar_connector import CalendarConnector
from config.config import Config


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
            "ToDo": {"rich_text": [{"plain_text": "Todo - " + name, "href": href}]},
        },
    }


def load_author():
    text = Path(ROOT / "payload_examples.txt").read_text()
    match = re.search(r"\"author\": \"([^\"]+)\"", text)
    return match.group(1)


class MockResponse:
    """Simple mock for aiohttp response."""

    def __init__(self, status: int, data: Dict[str, Any]):
        self.status = status
        self._data = data

    async def json(self) -> Dict[str, Any]:
        return self._data

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return None


class DummySession:
    """Session that records calls and returns predefined responses."""

    def __init__(self):
        self.post_calls: List[Tuple[str, Dict[str, str], Dict[str, Any]]] = []
        self.post_response: MockResponse | None = None
        self.closed = False

    def post(self, url: str, headers: Dict[str, str], json: Dict[str, Any]):
        self.post_calls.append((url, headers, json))
        return self.post_response

    async def close(self):
        self.closed = True


@pytest.mark.asyncio
async def test_create_day_off_event_success(tmp_path, monkeypatch):
    page = load_team_directory()
    name = page["properties"]["Name"]["title"][0]["plain_text"]
    event_id = page["id"]
    log_file = tmp_path / "dayoff_success_log.txt"
    log_file.write_text(f"Input: user={name}, date=2024-02-05\n")

    Config.CALENDAR_ID = "CAL_ID"
    monkeypatch.setattr(cc, "base_headers", lambda: {"Authorization": "Bearer token"})

    session = DummySession()
    session.post_response = MockResponse(200, {"id": event_id})

    connector = CalendarConnector(session=session)

    result = await connector.create_day_off_event(name, "2024-02-05")
    with open(log_file, "a") as f:
        f.write("Step: called create_day_off_event\n")
        f.write(f"Output: {result}\n")

    assert session.post_calls
    url, headers, payload = session.post_calls[0]
    assert url == "https://www.googleapis.com/calendar/v3/calendars/CAL_ID/events"
    assert headers["Authorization"] == "Bearer token"
    assert payload["summary"] == f"Day-off: {name}"
    assert payload["start"] == {"date": "2024-02-05"}
    assert result == {"status": "ok", "event_id": event_id}


@pytest.mark.asyncio
async def test_create_day_off_event_failure(tmp_path, monkeypatch):
    page = load_team_directory()
    name = page["properties"]["Name"]["title"][0]["plain_text"]
    author = load_author()
    log_file = tmp_path / "dayoff_failure_log.txt"
    log_file.write_text(f"Input: user={name}, date=2024-02-05\n")

    Config.CALENDAR_ID = "CAL_ID"
    monkeypatch.setattr(cc, "base_headers", lambda: {"Authorization": "Bearer token"})

    session = DummySession()
    session.post_response = MockResponse(500, {"error": author})

    connector = CalendarConnector(session=session)

    result = await connector.create_day_off_event(name, "2024-02-05")
    with open(log_file, "a") as f:
        f.write("Step: called create_day_off_event\n")
        f.write(f"Output: {result}\n")

    assert session.post_calls
    assert result == {"status": "error", "message": author}


@pytest.mark.asyncio
async def test_create_vacation_event_success(tmp_path, monkeypatch):
    page = load_team_directory()
    name = page["properties"]["Name"]["title"][0]["plain_text"]
    event_id = page["id"]
    log_file = tmp_path / "vacation_success_log.txt"
    log_file.write_text(f"Input: user={name}, start=2024-02-05, end=2024-02-10\n")

    Config.CALENDAR_ID = "CAL_ID"
    monkeypatch.setattr(cc, "base_headers", lambda: {"Authorization": "Bearer token"})

    session = DummySession()
    session.post_response = MockResponse(200, {"id": event_id})

    connector = CalendarConnector(session=session)

    result = await connector.create_vacation_event(
        name, "2024-02-05", "2024-02-10", "Europe/Kyiv"
    )
    with open(log_file, "a") as f:
        f.write("Step: called create_vacation_event\n")
        f.write(f"Output: {result}\n")

    assert session.post_calls
    url, headers, payload = session.post_calls[0]
    assert url == "https://www.googleapis.com/calendar/v3/calendars/CAL_ID/events"
    assert headers["Authorization"] == "Bearer token"
    assert payload["summary"] == f"Vacation: {name}"
    assert payload["start"] == {
        "dateTime": "2024-02-05T00:00:00",
        "timeZone": "Europe/Kyiv",
    }
    assert result == {"status": "ok", "event_id": event_id}


@pytest.mark.asyncio
async def test_create_vacation_event_failure(tmp_path, monkeypatch):
    page = load_team_directory()
    name = page["properties"]["Name"]["title"][0]["plain_text"]
    author = load_author()
    log_file = tmp_path / "vacation_failure_log.txt"
    log_file.write_text(f"Input: user={name}, start=2024-02-05, end=2024-02-10\n")

    Config.CALENDAR_ID = "CAL_ID"
    monkeypatch.setattr(cc, "base_headers", lambda: {"Authorization": "Bearer token"})

    session = DummySession()
    session.post_response = MockResponse(500, {"error": author})

    connector = CalendarConnector(session=session)

    result = await connector.create_vacation_event(
        name, "2024-02-05", "2024-02-10", "Europe/Kyiv"
    )
    with open(log_file, "a") as f:
        f.write("Step: called create_vacation_event\n")
        f.write(f"Output: {result}\n")

    assert session.post_calls
    assert result == {"status": "error", "message": author}
