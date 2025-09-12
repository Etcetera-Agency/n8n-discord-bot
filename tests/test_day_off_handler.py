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
    DATABASE_URL = "sqlite://"
    NOTION_TEAM_DIRECTORY_DB_ID = ""
    NOTION_TOKEN = ""
    NOTION_WORKLOAD_DB_ID = ""
    NOTION_PROFILE_STATS_DB_ID = ""
    SESSION_TTL = 1


config_mod = types.SimpleNamespace(
    Config=DummyConfig, logger=logging.getLogger("test"), Strings=object()
)
sys.modules["config"] = config_mod

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


def load_author() -> str:
    text = Path(ROOT / "responses").read_text()
    return re.search(r'plain_text": "([^\"]+Lernichenko)', text).group(1)


class DummyCalendar:
    def __init__(self, fail: bool = False):
        self.calls = []
        self.fail = fail

    async def create_day_off_event(self, name: str, date: str):
        self.calls.append((name, date))
        if self.fail:
            return {"status": "error", "message": "boom"}
        return {"status": "ok", "event_id": "1"}


class DummySteps:
    def __init__(self):
        self.calls = []

    async def upsert_step(self, session_id: str, step: str, completed: bool):
        self.calls.append((session_id, step, completed))
        return {"status": "ok"}


@pytest.mark.asyncio
async def test_no_dates(tmp_path, monkeypatch):
    log = tmp_path / "no_dates_log.txt"
    log.write_text("Input: Nothing\n")

    cal = DummyCalendar()
    steps = DummySteps()
    monkeypatch.setattr(day_off, "calendar", cal)
    monkeypatch.setattr(day_off, "_steps_db", steps)

    payload = load_payload_example("Day Off Slash Command Payload (e.g., /day_off_nextweek)")
    payload["command"] = "day_off_thisweek"
    payload["result"]["value"] = "Nothing"
    payload["author"] = load_author()
    payload["channelId"] = "123"

    with open(log, "a") as f:
        f.write("Step: handle\n")
    out = await day_off.handle(payload)
    with open(log, "a") as f:
        f.write(f"Output: {out}\n")

    assert not cal.calls
    assert steps.calls == [("123", "day_off_thisweek", True)]
    assert out == "Записав! Записав! Вихідних не береш."


@pytest.mark.asyncio
async def test_list_with_nothing(tmp_path, monkeypatch):
    log = tmp_path / "list_nothing_log.txt"
    log.write_text("Input: ['Nothing']\n")

    cal = DummyCalendar()
    steps = DummySteps()
    monkeypatch.setattr(day_off, "calendar", cal)
    monkeypatch.setattr(day_off, "_steps_db", steps)

    payload = load_payload_example("Day Off Slash Command Payload (e.g., /day_off_nextweek)")
    payload["command"] = "day_off_thisweek"
    payload["result"]["value"] = ["Nothing"]
    payload["author"] = load_author()
    payload["channelId"] = "123"

    with open(log, "a") as f:
        f.write("Step: handle\n")
    out = await day_off.handle(payload)
    with open(log, "a") as f:
        f.write(f"Output: {out}\n")

    assert not cal.calls
    assert steps.calls == [("123", "day_off_thisweek", True)]
    assert out == "Записав! Записав! Вихідних не береш."


@pytest.mark.asyncio
async def test_one_date(tmp_path, monkeypatch):
    log = tmp_path / "one_date_log.txt"
    log.write_text("Input: one date\n")

    cal = DummyCalendar()
    steps = DummySteps()
    monkeypatch.setattr(day_off, "calendar", cal)
    monkeypatch.setattr(day_off, "_steps_db", steps)

    payload = load_payload_example("Day Off Slash Command Payload (e.g., /day_off_nextweek)")
    payload["command"] = "day_off_thisweek"
    payload["result"]["value"] = ["2024-02-05"]
    payload["author"] = load_author()
    payload["channelId"] = "123"

    with open(log, "a") as f:
        f.write("Step: handle\n")
    out = await day_off.handle(payload)
    with open(log, "a") as f:
        f.write(f"Output: {out}\n")

    assert cal.calls == [(load_author(), "2024-02-05")]
    assert steps.calls == [("123", "day_off_thisweek", True)]
    expected = (
        f"Вихідний: {format_date_ua('2024-02-05')} записано.\n"
        "Не забудь попередити клієнтів.\n"
    )
    assert out == expected


@pytest.mark.asyncio
async def test_many_dates(tmp_path, monkeypatch):
    log = tmp_path / "many_dates_log.txt"
    log.write_text("Input: many dates\n")

    cal = DummyCalendar()
    steps = DummySteps()
    monkeypatch.setattr(day_off, "calendar", cal)
    monkeypatch.setattr(day_off, "_steps_db", steps)

    payload = load_payload_example("Day Off Slash Command Payload (e.g., /day_off_nextweek)")
    payload["command"] = "day_off_nextweek"
    payload["result"]["value"] = ["2024-02-05", "2024-02-06"]
    payload["author"] = load_author()
    payload["channelId"] = "123"

    with open(log, "a") as f:
        f.write("Step: handle\n")
    out = await day_off.handle(payload)
    with open(log, "a") as f:
        f.write(f"Output: {out}\n")

    assert cal.calls == [
        (load_author(), "2024-02-05"),
        (load_author(), "2024-02-06"),
    ]
    assert steps.calls == [("123", "day_off_nextweek", True)]
    formatted = ", ".join([
        format_date_ua("2024-02-05"),
        format_date_ua("2024-02-06"),
    ])
    expected = (
        f"Вихідні: {formatted} записані.\n"
        "Не забудь попередити клієнтів.\n"
    )
    assert out == expected


@pytest.mark.asyncio
async def test_calendar_error(tmp_path, monkeypatch):
    log = tmp_path / "calendar_error_log.txt"
    log.write_text("Input: calendar error\n")

    cal = DummyCalendar(fail=True)
    steps = DummySteps()
    monkeypatch.setattr(day_off, "calendar", cal)
    monkeypatch.setattr(day_off, "_steps_db", steps)

    payload = load_payload_example("Day Off Slash Command Payload (e.g., /day_off_nextweek)")
    payload["command"] = "day_off_nextweek"
    payload["result"]["value"] = ["2024-02-05"]
    payload["author"] = load_author()
    payload["channelId"] = "123"

    with open(log, "a") as f:
        f.write("Step: handle\n")
    out = await day_off.handle(payload)
    with open(log, "a") as f:
        f.write(f"Output: {out}\n")

    assert cal.calls == [(load_author(), "2024-02-05")]
    assert steps.calls == []
    assert out == "boom"


@pytest.mark.asyncio
async def test_single_string_value(tmp_path, monkeypatch):
    log = tmp_path / "single_string_log.txt"
    log.write_text("Input: single string value\n")

    cal = DummyCalendar()
    steps = DummySteps()
    monkeypatch.setattr(day_off, "calendar", cal)
    monkeypatch.setattr(day_off, "_steps_db", steps)

    payload = load_payload_example("Day Off Slash Command Payload (e.g., /day_off_nextweek)")
    payload["command"] = "day_off_thisweek"
    payload["result"]["value"] = "2024-02-05"
    payload["author"] = load_author()
    payload["channelId"] = "123"

    with open(log, "a") as f:
        f.write("Step: handle\n")
    out = await day_off.handle(payload)
    with open(log, "a") as f:
        f.write(f"Output: {out}\n")

    assert cal.calls == [(load_author(), "2024-02-05")]
    assert steps.calls == [("123", "day_off_thisweek", True)]
    expected = (
        f"Вихідний: {format_date_ua('2024-02-05')} записано.\n"
        "Не забудь попередити клієнтів.\n"
    )
    assert out == expected


@pytest.mark.asyncio
async def test_days_selected_key(tmp_path, monkeypatch):
    log = tmp_path / "days_selected_log.txt"
    log.write_text("Input: daysSelected key\n")

    cal = DummyCalendar()
    steps = DummySteps()
    monkeypatch.setattr(day_off, "calendar", cal)
    monkeypatch.setattr(day_off, "_steps_db", steps)

    payload = load_payload_example("Day Off Slash Command Payload (e.g., /day_off_nextweek)")
    payload["command"] = "day_off_nextweek"
    payload["result"].pop("value", None)
    payload["result"]["daysSelected"] = ["2024-02-05", "2024-02-06"]
    payload["author"] = load_author()
    payload["channelId"] = "123"

    with open(log, "a") as f:
        f.write("Step: handle\n")
    out = await day_off.handle(payload)
    with open(log, "a") as f:
        f.write(f"Output: {out}\n")

    assert cal.calls == [
        (load_author(), "2024-02-05"),
        (load_author(), "2024-02-06"),
    ]
    assert steps.calls == [("123", "day_off_nextweek", True)]
    formatted = ", ".join([
        format_date_ua("2024-02-05"),
        format_date_ua("2024-02-06"),
    ])
    expected = (
        f"Вихідні: {formatted} записані.\n"
        "Не забудь попередити клієнтів.\n"
    )
    assert out == expected


@pytest.mark.asyncio
async def test_invalid_date_format(tmp_path, monkeypatch):
    log = tmp_path / "invalid_date_log.txt"
    log.write_text("Input: invalid date\n")

    cal = DummyCalendar()
    steps = DummySteps()
    monkeypatch.setattr(day_off, "calendar", cal)
    monkeypatch.setattr(day_off, "_steps_db", steps)

    payload = load_payload_example("Day Off Slash Command Payload (e.g., /day_off_nextweek)")
    payload["command"] = "day_off_nextweek"
    payload["result"]["value"] = ["2024-02-30"]
    payload["author"] = load_author()
    payload["channelId"] = "123"

    with open(log, "a") as f:
        f.write("Step: handle\n")
    out = await day_off.handle(payload)
    with open(log, "a") as f:
        f.write(f"Output: {out}\n")

    assert cal.calls == []
    assert steps.calls == []
    assert out == "Некоректна дата: 2024-02-30"

