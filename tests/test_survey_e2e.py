import sys
import json
import re
from pathlib import Path
import pytest
import types
import logging

ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT))
sys.path.append(str(ROOT / "services"))


class DummyConfig:
    DATABASE_URL = "sqlite://"
    NOTION_TEAM_DIRECTORY_DB_ID = ""
    NOTION_TOKEN = ""
    NOTION_WORKLOAD_DB_ID = ""
    NOTION_PROFILE_STATS_DB_ID = ""
    SESSION_TTL = 1


sys.modules["config"] = types.SimpleNamespace(
    Config=DummyConfig, logger=logging.getLogger("test"), Strings=object()
)

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

import router
from services.survey_models import SurveyStep

survey_manager = router.survey_manager


def load_payload_example(title: str) -> dict:
    text = Path(ROOT / "payload_examples.txt").read_text()
    start = text.index(title)
    match = re.search(r"```json\n(.*?)\n```", text[start:], re.DOTALL)
    return json.loads(match.group(1))


def load_notion_lookup():
    text = Path(ROOT / "responses").read_text()
    name = re.search(r'plain_text": "([^"]+Lernichenko)"', text).group(1)
    todo_url = re.search(r'https://www.notion.so/[0-9a-f-]+', text).group(0)
    return {"results": [{"name": name, "discord_id": "321", "channel_id": "123", "to_do": todo_url}]}


def make_payload(title: str, step_name: str) -> dict:
    payload = load_payload_example(title)
    payload["userId"] = "321"
    payload["channelId"] = "123"
    payload["sessionId"] = "123_321"
    payload["result"]["stepName"] = step_name
    return payload


@pytest.mark.asyncio
async def test_survey_monday_full(monkeypatch):
    async def lookup(channel_id):
        return load_notion_lookup()

    monkeypatch.setattr(router._notio, "find_team_directory_by_channel", lookup)

    async def wt(payload):
        return "wt"

    async def wn(payload):
        return "wn"

    async def conn(payload):
        return "conn"

    async def day(payload):
        return "day"

    monkeypatch.setitem(router.HANDLERS, "workload_today", wt)
    monkeypatch.setitem(router.HANDLERS, "workload_nextweek", wn)
    monkeypatch.setitem(router.HANDLERS, "connects_thisweek", conn)
    monkeypatch.setitem(router.HANDLERS, "day_off_nextweek", day)

    survey_manager.create_survey(
        "321",
        "123",
        [
            SurveyStep(name="workload_today"),
            SurveyStep(name="workload_nextweek"),
            SurveyStep(name="connects_thisweek"),
            SurveyStep(name="day_off_nextweek"),
        ],
        "sess",
    )

    p1 = make_payload("Survey Step Submission Payload (Workload)", "workload_today")
    r1 = await router.dispatch(p1)
    assert r1 == {"output": "wt"}
    survey_manager.get_survey("123").next_step()

    p2 = make_payload("Survey Step Submission Payload (Workload)", "workload_nextweek")
    r2 = await router.dispatch(p2)
    assert r2 == {"output": "wn"}
    survey_manager.get_survey("123").next_step()

    p3 = make_payload("Survey Step Submission Payload (Connects)", "connects_thisweek")
    r3 = await router.dispatch(p3)
    assert r3 == {"output": "conn"}
    survey_manager.get_survey("123").next_step()

    p4 = make_payload("Survey Step Submission Payload (Day Off)", "day_off_nextweek")
    r4 = await router.dispatch(p4)
    assert r4 == {"output": "day"}
    await survey_manager.end_survey("123")
    assert survey_manager.get_survey("123") is None


@pytest.mark.asyncio
async def test_survey_tuesday_missing_nextweek(monkeypatch):
    async def lookup(channel_id):
        return load_notion_lookup()

    monkeypatch.setattr(router._notio, "find_team_directory_by_channel", lookup)

    async def wt(payload):
        return "wt"

    async def conn(payload):
        return "conn"

    async def day(payload):
        return "day"

    monkeypatch.setitem(router.HANDLERS, "workload_today", wt)
    monkeypatch.setitem(router.HANDLERS, "connects_thisweek", conn)
    monkeypatch.setitem(router.HANDLERS, "day_off_nextweek", day)

    survey_manager.create_survey(
        "321",
        "123",
        [
            SurveyStep(name="workload_today"),
            SurveyStep(name="workload_nextweek"),
            SurveyStep(name="connects_thisweek"),
            SurveyStep(name="day_off_nextweek"),
        ],
        "sess2",
    )

    p1 = make_payload("Survey Step Submission Payload (Workload)", "workload_today")
    await router.dispatch(p1)
    s = survey_manager.get_survey("123")
    s.next_step()
    s.next_step()
    p3 = make_payload("Survey Step Submission Payload (Connects)", "connects_thisweek")
    await router.dispatch(p3)
    s.next_step()
    p4 = make_payload("Survey Step Submission Payload (Day Off)", "day_off_nextweek")
    r = await router.dispatch(p4)
    assert r == {"output": "day"}
    await survey_manager.end_survey("123")


@pytest.mark.asyncio
async def test_survey_friday_full(monkeypatch):
    async def lookup(channel_id):
        return load_notion_lookup()

    monkeypatch.setattr(router._notio, "find_team_directory_by_channel", lookup)

    async def wt(payload):
        return "wt"

    async def wn(payload):
        return "wn"

    async def conn(payload):
        return "conn"

    async def day(payload):
        return "day"

    monkeypatch.setitem(router.HANDLERS, "workload_today", wt)
    monkeypatch.setitem(router.HANDLERS, "workload_nextweek", wn)
    monkeypatch.setitem(router.HANDLERS, "connects_thisweek", conn)
    monkeypatch.setitem(router.HANDLERS, "day_off_nextweek", day)

    survey_manager.create_survey(
        "321",
        "123",
        [
            SurveyStep(name="workload_today"),
            SurveyStep(name="workload_nextweek"),
            SurveyStep(name="connects_thisweek"),
            SurveyStep(name="day_off_nextweek"),
        ],
        "sess3",
    )

    await router.dispatch(make_payload("Survey Step Submission Payload (Workload)", "workload_today"))
    survey_manager.get_survey("123").next_step()
    await router.dispatch(make_payload("Survey Step Submission Payload (Workload)", "workload_nextweek"))
    survey_manager.get_survey("123").next_step()
    await router.dispatch(make_payload("Survey Step Submission Payload (Connects)", "connects_thisweek"))
    survey_manager.get_survey("123").next_step()
    r = await router.dispatch(make_payload("Survey Step Submission Payload (Day Off)", "day_off_nextweek"))
    assert r == {"output": "day"}
    await survey_manager.end_survey("123")
    assert survey_manager.get_survey("123") is None
