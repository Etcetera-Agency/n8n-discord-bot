import json
import re
from pathlib import Path
import sys
import types
import logging
import pytest


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "services"))

# Stub google modules required by calendar connector
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
    SESSION_TTL = 1


sys.modules["config"] = types.SimpleNamespace(
    Config=DummyConfig,
    logger=logging.getLogger("test"),
    Strings=types.SimpleNamespace(
        TRY_AGAIN_LATER="Спробуй трохи піздніше. Я тут пораюсь по хаті."
    ),
)

from services.cmd import vacation


class FakeDB:
    def __init__(self, *_):
        self.calls = []
        self.closed = False

    async def upsert_step(self, session_id, step_name, completed):
        self.calls.append((session_id, step_name, completed))

    async def close(self):
        self.closed = True


def load_payload(title: str) -> dict:
    text = Path(ROOT / "payload_examples.txt").read_text()
    start = text.index(title)
    match = re.search(r"```json\n(.*?)\n```", text[start:], re.DOTALL)
    return json.loads(match.group(1))


def load_response_data():
    text = Path(ROOT / "responses").read_text()
    dates = re.findall(r"(\d{4}-\d{2}-\d{2})", text)
    event_id = re.search(r'id": "([0-9a-f-]{36})"', text).group(1)
    return dates[0], dates[1], event_id


@pytest.mark.asyncio
async def test_handle_vacation_success(tmp_path, monkeypatch):
    log = tmp_path / "vacation_success_log.txt"
    log.write_text("Input: vacation survey step\n")

    start_date, end_date, event_id = load_response_data()
    start_iso = f"{start_date}T00:00:00+03:00"
    end_iso = f"{end_date}T00:00:00+03:00"
    payload = load_payload("/vacation Command Payload")
    payload["result"]["start_date"] = start_iso
    payload["result"]["end_date"] = end_iso

    fake_db = FakeDB()
    monkeypatch.setattr(vacation, "SurveyStepsDB", lambda *_: fake_db)
    monkeypatch.setattr(vacation, "Config", types.SimpleNamespace(DATABASE_URL="sqlite://"))

    async def fake_create(name, start, end, tz):
        assert name == payload["author"]
        assert start == start_date and end == end_date and tz == "Europe/Kyiv"
        return {"status": "ok", "event_id": event_id}

    monkeypatch.setattr(
        vacation, "calendar", types.SimpleNamespace(create_vacation_event=fake_create)
    )

    with open(log, "a") as f:
        f.write("Step: handle\n")
    result = await vacation.handle(payload)
    with open(log, "a") as f:
        f.write(f"Output: {result}\n")

    # Compute expected formatted dates
    def fmt(d):
        dt = vacation.datetime.fromisoformat(d)
        return (
            f"{vacation.WEEKDAYS[dt.weekday()]} "
            f"{dt.day:02d} {vacation.MONTHS[dt.month-1]} {dt.year}"
        )

    expected = f"Записав! Відпустка: {fmt(start_iso)}—{fmt(end_iso)}."
    assert result == expected


@pytest.mark.asyncio
async def test_handle_vacation_calendar_error(tmp_path, monkeypatch):
    log = tmp_path / "vacation_error_log.txt"
    log.write_text("Input: vacation calendar error\n")

    start_date, end_date, _ = load_response_data()
    start_iso = f"{start_date}T00:00:00+03:00"
    end_iso = f"{end_date}T00:00:00+03:00"
    payload = load_payload("/vacation Command Payload")
    payload["result"]["start_date"] = start_iso
    payload["result"]["end_date"] = end_iso

    fake_db = FakeDB()
    monkeypatch.setattr(vacation, "SurveyStepsDB", lambda *_: fake_db)
    monkeypatch.setattr(vacation, "Config", types.SimpleNamespace(DATABASE_URL="sqlite://"))

    async def fake_create(name, start, end, tz):
        raise RuntimeError("calendar down")

    monkeypatch.setattr(
        vacation, "calendar", types.SimpleNamespace(create_vacation_event=fake_create)
    )

    with open(log, "a") as f:
        f.write("Step: handle\n")
    result = await vacation.handle(payload)
    with open(log, "a") as f:
        f.write(f"Output: {result}\n")

    assert result == "Спробуй трохи піздніше. Я тут пораюсь по хаті."


@pytest.mark.asyncio
async def test_vacation_e2e(tmp_path, monkeypatch):
    log = tmp_path / "vacation_e2e_log.txt"
    log.write_text("Input: dispatch vacation\n")

    import router

    async def fake_lookup(channel_id):
        text = Path(ROOT / "responses").read_text()
        name = re.search(r'plain_text": "([^\"]+Lernichenko)"', text).group(1)
        return {"results": [{"name": name, "discord_id": "321", "channel_id": "123"}]}

    start_date, end_date, event_id = load_response_data()
    start_iso = f"{start_date}T00:00:00+03:00"
    end_iso = f"{end_date}T00:00:00+03:00"

    async def fake_create(name, start, end, tz):
        assert start == start_date and end == end_date
        return {"status": "ok", "event_id": event_id}

    fake_db = FakeDB()
    monkeypatch.setattr(vacation, "SurveyStepsDB", lambda *_: fake_db)
    monkeypatch.setattr(vacation, "Config", types.SimpleNamespace(DATABASE_URL="sqlite://"))
    monkeypatch.setattr(router._notio, "find_team_directory_by_channel", fake_lookup)
    monkeypatch.setattr(
        vacation, "calendar", types.SimpleNamespace(create_vacation_event=fake_create)
    )

    payload = load_payload("/vacation Command Payload")
    payload["channelId"] = "123"
    payload["userId"] = "321"
    payload["sessionId"] = "123_321"
    payload["result"]["start_date"] = start_iso
    payload["result"]["end_date"] = end_iso

    with open(log, "a") as f:
        f.write("Step: router.dispatch\n")
    result = (await router.dispatch(payload)).to_dict()
    with open(log, "a") as f:
        f.write(f"Output: {result}\n")

    def fmt(d):
        dt = vacation.datetime.fromisoformat(d)
        return (
            f"{vacation.WEEKDAYS[dt.weekday()]} "
            f"{dt.day:02d} {vacation.MONTHS[dt.month-1]} {dt.year}"
        )

    expected = f"Записав! Відпустка: {fmt(start_iso)}—{fmt(end_iso)}."
    assert result == {"output": expected}


@pytest.mark.asyncio
async def test_handle_vacation_records_step(monkeypatch, tmp_path):
    log = tmp_path / "vacation_db_log.txt"
    log.write_text("Input: vacation survey db\n")

    start_date, end_date, _ = load_response_data()
    start_iso = f"{start_date}T00:00:00+03:00"
    end_iso = f"{end_date}T00:00:00+03:00"
    payload = load_payload("/vacation Command Payload")
    payload["result"]["start_date"] = start_iso
    payload["result"]["end_date"] = end_iso

    fake_db = FakeDB()
    monkeypatch.setattr(vacation, "SurveyStepsDB", lambda *_: fake_db)
    monkeypatch.setattr(vacation, "Config", types.SimpleNamespace(DATABASE_URL="sqlite://"))

    async def fake_create(name, start, end, tz):
        return {"status": "ok"}

    monkeypatch.setattr(
        vacation, "calendar", types.SimpleNamespace(create_vacation_event=fake_create)
    )

    result = await vacation.handle(payload)
    with open(log, "a") as f:
        f.write("Step: handle\n")
        f.write(f"Output: {result}\n")

    assert fake_db.calls == [(payload["channelId"], "vacation", True)]
    assert fake_db.closed
