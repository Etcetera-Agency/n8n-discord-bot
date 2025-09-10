import sys
import json
import re
from pathlib import Path
import types
import logging

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT))
sys.path.append(str(ROOT / "services"))


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
    DATABASE_URL = ""
    NOTION_TEAM_DIRECTORY_DB_ID = ""
    NOTION_TOKEN = ""
    NOTION_WORKLOAD_DB_ID = ""
    NOTION_PROFILE_STATS_DB_ID = ""
    SESSION_TTL = 1


config_mod = types.SimpleNamespace(
    Config=DummyConfig, logger=logging.getLogger("test"), Strings=object()
)
sys.modules["config"] = config_mod

import router
import services.cmd.day_off as day_off
from services.date_utils import format_date_ua


def load_payload_example(title: str) -> dict:
    text = Path(ROOT / "payload_examples.txt").read_text()
    start = text.index(title)
    snippet = text[start:]
    first = snippet.index("{")
    depth = 0
    end = first
    for i, ch in enumerate(snippet[first:]):
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                end = first + i + 1
                break
    return json.loads(snippet[first:end])


def load_notion_lookup():
    text = Path(ROOT / "responses").read_text()
    name = re.search(r'plain_text": "([^\"]+Lernichenko)', text).group(1)
    todo_url = re.search(r'https://www.notion.so/[0-9a-f-]+', text).group(0)
    return {"results": [{"name": name, "discord_id": "321", "channel_id": "123", "to_do": todo_url}]}


class DummyCalendar:
    def __init__(self):
        self.calls = []

    async def create_day_off_event(self, name: str, date: str):
        self.calls.append((name, date))
        return {"status": "ok", "event_id": "1"}


class DummySteps:
    def __init__(self):
        self.calls = []

    async def upsert_step(self, session_id: str, step: str, completed: bool):
        self.calls.append((session_id, step, completed))
        return {"status": "ok"}


def _prepare(monkeypatch):
    async def lookup(channel_id):
        return load_notion_lookup()

    monkeypatch.setattr(router._notio, "find_team_directory_by_channel", lookup)
    cal = DummyCalendar()
    steps = DummySteps()
    monkeypatch.setattr(day_off, "calendar", cal)
    monkeypatch.setattr(day_off, "_steps_db", steps)
    return cal, steps


@pytest.mark.asyncio
async def test_day_off_thisweek_e2e(tmp_path, monkeypatch):
    log = tmp_path / "day_off_thisweek_log.txt"
    log.write_text("Input: day_off_thisweek\n")

    cal, steps = _prepare(monkeypatch)

    payload = load_payload_example("Day Off Slash Command Payload (e.g., /day_off_nextweek)")
    payload.update({"command": "day_off_thisweek", "result": {"value": ["2024-02-05"]}})
    payload["channelId"] = "123"
    payload["sessionId"] = "123_321"
    payload["userId"] = "321"

    with open(log, "a") as f:
        f.write("Step: dispatch\n")
    result = await router.dispatch(payload)
    with open(log, "a") as f:
        f.write(f"Output: {result}\n")

    name = load_notion_lookup()["results"][0]["name"]
    assert cal.calls == [(name, "2024-02-05")]
    assert steps.calls == [("123", "day_off_thisweek", True)]
    expected = (
        f"Вихідний: {format_date_ua('2024-02-05')} записано.\n"
        "Не забудь попередити клієнтів.\n"
    )
    assert result == {"output": expected}


@pytest.mark.asyncio
async def test_day_off_nextweek_e2e(tmp_path, monkeypatch):
    log = tmp_path / "day_off_nextweek_log.txt"
    log.write_text("Input: day_off_nextweek\n")

    cal, steps = _prepare(monkeypatch)

    payload = load_payload_example("Day Off Slash Command Payload (e.g., /day_off_nextweek)")
    payload.update({"command": "day_off_nextweek", "result": {"value": ["2024-02-05", "2024-02-06"]}})
    payload["channelId"] = "123"
    payload["sessionId"] = "123_321"
    payload["userId"] = "321"

    with open(log, "a") as f:
        f.write("Step: dispatch\n")
    result = await router.dispatch(payload)
    with open(log, "a") as f:
        f.write(f"Output: {result}\n")

    name = load_notion_lookup()["results"][0]["name"]
    assert cal.calls == [(name, "2024-02-05"), (name, "2024-02-06")]
    assert steps.calls == [("123", "day_off_nextweek", True)]
    formatted = ", ".join([
        format_date_ua("2024-02-05"),
        format_date_ua("2024-02-06"),
    ])
    expected = (
        f"Вихідні: {formatted} записані.\n"
        "Не забудь попередити клієнтів.\n"
    )
    assert result == {"output": expected}

