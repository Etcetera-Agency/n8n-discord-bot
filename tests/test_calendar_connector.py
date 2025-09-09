import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT))
sys.path.append(str(ROOT / "services"))

import calendar_connector as cc
from calendar_connector import CalendarConnector
from config.config import Config


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
    log_file = tmp_path / "dayoff_success_log.txt"
    log_file.write_text("Input: user=Roman Lernichenko, date=2024-02-05\n")

    Config.CALENDAR_ID = "CAL_ID"
    monkeypatch.setattr(cc, "base_headers", lambda: {"Authorization": "Bearer token"})

    session = DummySession()
    session.post_response = MockResponse(200, {"id": "CAL_EVENT_ID"})

    connector = CalendarConnector(session=session)

    result = await connector.create_day_off_event("Roman Lernichenko", "2024-02-05")
    with open(log_file, "a") as f:
        f.write("Step: called create_day_off_event\n")
        f.write(f"Output: {result}\n")

    assert session.post_calls
    url, headers, payload = session.post_calls[0]
    assert url == "https://www.googleapis.com/calendar/v3/calendars/CAL_ID/events"
    assert headers["Authorization"] == "Bearer token"
    assert payload["summary"] == "Day-off: Roman Lernichenko"
    assert payload["start"] == {"date": "2024-02-05"}
    assert result == {"status": "ok", "event_id": "CAL_EVENT_ID"}


@pytest.mark.asyncio
async def test_create_day_off_event_failure(tmp_path, monkeypatch):
    log_file = tmp_path / "dayoff_failure_log.txt"
    log_file.write_text("Input: user=Roman Lernichenko, date=2024-02-05\n")

    Config.CALENDAR_ID = "CAL_ID"
    monkeypatch.setattr(cc, "base_headers", lambda: {"Authorization": "Bearer token"})

    session = DummySession()
    session.post_response = MockResponse(500, {"error": "down"})

    connector = CalendarConnector(session=session)

    result = await connector.create_day_off_event("Roman Lernichenko", "2024-02-05")
    with open(log_file, "a") as f:
        f.write("Step: called create_day_off_event\n")
        f.write(f"Output: {result}\n")

    assert session.post_calls
    assert result == {"status": "error", "message": "down"}


@pytest.mark.asyncio
async def test_create_vacation_event_success(tmp_path, monkeypatch):
    log_file = tmp_path / "vacation_success_log.txt"
    log_file.write_text("Input: user=Roman Lernichenko, start=2024-02-05, end=2024-02-10\n")

    Config.CALENDAR_ID = "CAL_ID"
    monkeypatch.setattr(cc, "base_headers", lambda: {"Authorization": "Bearer token"})

    session = DummySession()
    session.post_response = MockResponse(200, {"id": "VAC_EVENT_ID"})

    connector = CalendarConnector(session=session)

    result = await connector.create_vacation_event(
        "Roman Lernichenko", "2024-02-05", "2024-02-10", "Europe/Kyiv"
    )
    with open(log_file, "a") as f:
        f.write("Step: called create_vacation_event\n")
        f.write(f"Output: {result}\n")

    assert session.post_calls
    url, headers, payload = session.post_calls[0]
    assert url == "https://www.googleapis.com/calendar/v3/calendars/CAL_ID/events"
    assert headers["Authorization"] == "Bearer token"
    assert payload["summary"] == "Vacation: Roman Lernichenko"
    assert payload["start"] == {
        "dateTime": "2024-02-05T00:00:00",
        "timeZone": "Europe/Kyiv",
    }
    assert result == {"status": "ok", "event_id": "VAC_EVENT_ID"}


@pytest.mark.asyncio
async def test_create_vacation_event_failure(tmp_path, monkeypatch):
    log_file = tmp_path / "vacation_failure_log.txt"
    log_file.write_text("Input: user=Roman Lernichenko, start=2024-02-05, end=2024-02-10\n")

    Config.CALENDAR_ID = "CAL_ID"
    monkeypatch.setattr(cc, "base_headers", lambda: {"Authorization": "Bearer token"})

    session = DummySession()
    session.post_response = MockResponse(500, {"error": "down"})

    connector = CalendarConnector(session=session)

    result = await connector.create_vacation_event(
        "Roman Lernichenko", "2024-02-05", "2024-02-10", "Europe/Kyiv"
    )
    with open(log_file, "a") as f:
        f.write("Step: called create_vacation_event\n")
        f.write(f"Output: {result}\n")

    assert session.post_calls
    assert result == {"status": "error", "message": "down"}
