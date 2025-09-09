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
    N8N_WEBHOOK_URL = ""
    WEBHOOK_AUTH_TOKEN = ""
    SESSION_TTL = 1


sys.modules["config"] = types.SimpleNamespace(
    Config=DummyConfig, logger=logging.getLogger("test"), Strings=object()
)

from services.cmd import vacation


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
    payload = load_payload("/vacation Command Payload")
    payload.update({
        "command": "survey",
        "result": {
            "stepName": "vacation",
            "start_date": start_date,
            "end_date": end_date,
        },
        "userId": "321",
        "channelId": "123",
        "sessionId": "123_321",
    })

    async def fake_create(name, start, end, tz):
        assert name == payload["author"]
        assert start == start_date and end == end_date and tz == "Europe/Kyiv"
        return {"status": "ok", "event_id": event_id}

    called = {}

    class DummySurvey:
        async def upsert_step(self, session_id, step, completed):
            called["args"] = (session_id, step, completed)

    monkeypatch.setattr(vacation, "calendar", types.SimpleNamespace(create_vacation_event=fake_create))
    monkeypatch.setattr(vacation, "survey_db", DummySurvey())

    with open(log, "a") as f:
        f.write("Step: handle\n")
    result = await vacation.handle(payload)
    with open(log, "a") as f:
        f.write(f"Output: {result}\n")

    assert called["args"] == ("321", "vacation", True)

    # Compute expected formatted dates
    def fmt(d):
        dt = vacation.datetime.fromisoformat(d)
        return f"{vacation.WEEKDAYS[dt.weekday()]} {dt.day:02d} {vacation.MONTHS[dt.month-1]}"

    expected = f"Записав! Відпустка: {fmt(start_date)}—{fmt(end_date)}."
    assert result == expected


@pytest.mark.asyncio
async def test_handle_vacation_calendar_error(tmp_path, monkeypatch):
    log = tmp_path / "vacation_error_log.txt"
    log.write_text("Input: vacation calendar error\n")

    start_date, end_date, _ = load_response_data()
    payload = load_payload("/vacation Command Payload")
    payload["result"]["start_date"] = start_date
    payload["result"]["end_date"] = end_date

    async def fake_create(name, start, end, tz):
        raise RuntimeError("calendar down")

    class DummySurvey:
        async def upsert_step(self, *args, **kwargs):
            raise AssertionError("should not be called")

    monkeypatch.setattr(vacation, "calendar", types.SimpleNamespace(create_vacation_event=fake_create))
    monkeypatch.setattr(vacation, "survey_db", DummySurvey())

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

    async def fake_create(name, start, end, tz):
        return {"status": "ok", "event_id": event_id}

    monkeypatch.setattr(router._notio, "find_team_directory_by_channel", fake_lookup)
    monkeypatch.setattr(vacation, "calendar", types.SimpleNamespace(create_vacation_event=fake_create))
    monkeypatch.setattr(vacation, "survey_db", None)

    payload = load_payload("/vacation Command Payload")
    payload["channelId"] = "123"
    payload["userId"] = "321"
    payload["sessionId"] = "123_321"
    payload["result"]["start_date"] = start_date
    payload["result"]["end_date"] = end_date

    with open(log, "a") as f:
        f.write("Step: router.dispatch\n")
    result = await router.dispatch(payload)
    with open(log, "a") as f:
        f.write(f"Output: {result}\n")

    def fmt(d):
        dt = vacation.datetime.fromisoformat(d)
        return f"{vacation.WEEKDAYS[dt.weekday()]} {dt.day:02d} {vacation.MONTHS[dt.month-1]}"

    expected = f"Записав! Відпустка: {fmt(start_date)}—{fmt(end_date)}."
    assert result == {"output": expected}
