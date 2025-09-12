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


def load_payload_example(title: str) -> dict:
    text = Path(ROOT / "payload_examples.txt").read_text()
    start = text.index(title)
    match = re.search(r"```json\n(.*?)\n```", text[start:], re.DOTALL)
    return json.loads(match.group(1))


def load_notion_lookup():
    text = Path(ROOT / "responses").read_text()
    name = re.search(r'plain_text": "([^"]+Lernichenko)"', text).group(1)
    todo_url = re.search(r'https://www.notion.so/[0-9a-f-]+', text).group(0)
    page_id = re.search(r'id": "([0-9a-f-]{36})"', text).group(1)
    return {
        "results": [
            {
                "id": page_id,
                "name": name,
                "discord_id": "321",
                "channel_id": "123",
                "to_do": todo_url,
            }
        ]
    }
# Stub config to avoid heavy imports
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

import router
from services.cmd import unregister as unregister_cmd

survey_manager = router.survey_manager


@pytest.mark.asyncio
async def test_dispatch_mention(tmp_path, monkeypatch):
    log = tmp_path / "mention_log.txt"
    log.write_text("Input: mention\n")

    async def fake_lookup(channel_id):
        return load_notion_lookup()

    monkeypatch.setattr(router._notio, "find_team_directory_by_channel", fake_lookup)
    payload = load_payload_example("!mention Command Payload")
    payload["message"] = "hi"
    payload["userId"] = "321"
    payload["channelId"] = "123"
    payload["sessionId"] = "123_321"
    with open(log, "a") as f:
        f.write("Step: dispatch\n")
    result = await router.dispatch(payload)
    with open(log, "a") as f:
        f.write(f"Output: {result}\n")
    assert result == {
        "output": "Я ще не вмію вільно розмовляти. Використовуй слеш команди <@321>. Почни із /"
    }


@pytest.mark.asyncio
async def test_dispatch_command(tmp_path, monkeypatch):
    log = tmp_path / "command_log.txt"
    log.write_text("Input: command\n")

    async def fake_lookup(channel_id):
        return load_notion_lookup()

    async def dummy(payload):
        return "ok"

    monkeypatch.setattr(router._notio, "find_team_directory_by_channel", fake_lookup)
    monkeypatch.setitem(router.HANDLERS, "dummy", dummy)
    payload = load_payload_example("Generic Slash Command Payload")
    payload.update({"command": "dummy", "result": {}})
    payload["channelId"] = "123"
    payload["userId"] = "321"
    payload["sessionId"] = "123_321"
    with open(log, "a") as f:
        f.write("Step: dispatch\n")
    result = await router.dispatch(payload)
    with open(log, "a") as f:
        f.write(f"Output: {result}\n")
    assert result == {"output": "ok"}


@pytest.mark.asyncio
async def test_dispatch_survey_end(tmp_path, monkeypatch):
    log = tmp_path / "survey_log.txt"
    log.write_text("Input: survey\n")

    async def fake_lookup(channel_id):
        return load_notion_lookup()

    async def step1(payload):
        return "done"

    monkeypatch.setattr(router._notio, "find_team_directory_by_channel", fake_lookup)
    monkeypatch.setitem(router.HANDLERS, "step1", step1)
    survey_manager.create_survey("321", "123", ["step1"], "sess")
    payload = load_payload_example("Survey Step Submission Payload (Workload)")
    payload.update({"command": "survey"})
    payload["result"]["stepName"] = "step1"
    payload["result"]["value"] = "v"
    payload["channelId"] = "123"
    payload["userId"] = "321"
    payload["sessionId"] = "123_321"
    with open(log, "a") as f:
        f.write("Step: dispatch\n")
    result = await router.dispatch(payload)
    with open(log, "a") as f:
        f.write(f"Output: {result}\n")
    assert result == {"output": "done"}
    assert survey_manager.get_survey("123") is not None
    survey_manager.remove_survey("123")


@pytest.mark.asyncio
async def test_dispatch_day_off_results(tmp_path, monkeypatch):
    log = tmp_path / "survey_dayoff_log.txt"
    log.write_text("Input: survey-dayoff\n")

    async def fake_lookup(channel_id):
        return load_notion_lookup()

    async def day(payload):
        return "done"

    monkeypatch.setattr(router._notio, "find_team_directory_by_channel", fake_lookup)
    monkeypatch.setitem(router.HANDLERS, "day_off_nextweek", day)
    survey_manager.create_survey("321", "123", ["day_off_nextweek"], "sess")
    payload = load_payload_example("Survey Step Submission Payload (Day Off)")
    payload["channelId"] = "123"
    payload["userId"] = "321"
    payload["sessionId"] = "123_321"
    payload["result"]["daysSelected"] = ["2025-09-16", "2025-09-21"]
    with open(log, "a") as f:
        f.write("Step: dispatch\n")
    result = await router.dispatch(payload)
    assert result == {"output": "done"}
    survey = survey_manager.get_survey("123")
    lookup = load_notion_lookup()
    assert survey.todo_url == lookup["results"][0]["to_do"]
    assert survey.results["day_off_nextweek"] == ["2025-09-16", "2025-09-21"]
    survey_manager.remove_survey("123")


@pytest.mark.asyncio
async def test_dispatch_survey_continue(tmp_path, monkeypatch):
    log = tmp_path / "survey_continue_log.txt"
    log.write_text("Input: survey-continue\n")

    async def fake_lookup(channel_id):
        return load_notion_lookup()

    async def step1(payload):
        return "step1"

    async def step2(payload):
        return "step2"

    monkeypatch.setattr(router._notio, "find_team_directory_by_channel", fake_lookup)
    monkeypatch.setitem(router.HANDLERS, "step1", step1)
    monkeypatch.setitem(router.HANDLERS, "step2", step2)
    survey_manager.create_survey("321", "123", ["step1", "step2"], "sess")
    payload = load_payload_example("Survey Step Submission Payload (Workload)")
    payload.update({"command": "survey"})
    payload["result"]["stepName"] = "step1"
    payload["result"]["value"] = "v"
    payload["channelId"] = "123"
    payload["userId"] = "321"
    payload["sessionId"] = "123_321"
    with open(log, "a") as f:
        f.write("Step: dispatch\n")
    result = await router.dispatch(payload)
    with open(log, "a") as f:
        f.write(f"Output: {result}\n")
    assert result == {"output": "step1"}
    assert survey_manager.get_survey("123") is not None


@pytest.mark.asyncio
async def test_dispatch_user_not_found(tmp_path, monkeypatch):
    log = tmp_path / "user_not_found_log.txt"
    log.write_text("Input: user-not-found\n")

    async def empty_lookup(channel_id):
        data = load_notion_lookup()
        data["results"] = []
        return data

    monkeypatch.setattr(router._notio, "find_team_directory_by_channel", empty_lookup)
    payload = load_payload_example("Generic Slash Command Payload")
    payload.update({"command": "dummy", "result": {}})
    payload["channelId"] = "123"
    payload["userId"] = "321"
    payload["sessionId"] = "123_321"
    result = await router.dispatch(payload)
    with open(log, "a") as f:
        f.write(f"Output: {result}\n")
    assert result == {"output": "Користувач не знайдений"}


@pytest.mark.asyncio
async def test_dispatch_register(tmp_path, monkeypatch):
    log = tmp_path / "register_e2e_log.txt"
    payload = load_payload_example("!register Command Payload")
    payload["userId"] = "321"
    payload["channelId"] = "123"
    payload["sessionId"] = "123_321"
    log.write_text(f"Input: {payload}\n")

    data = load_notion_lookup()
    data["results"][0]["discord_id"] = ""
    data["results"][0]["channel_id"] = ""

    async def router_lookup(channel_id):
        return data

    async def fake_find_channel(cid):
        return {"results": []}

    async def fake_find_name(name):
        return {"results": [{"id": "abc", "discord_id": "", "channel_id": ""}]}

    async def fake_update(pid, uid, cid):
        return {"status": "ok"}

    import services.cmd.register as reg
    monkeypatch.setattr(router._notio, "find_team_directory_by_channel", router_lookup)
    monkeypatch.setattr(reg._notio, "find_team_directory_by_channel", fake_find_channel)
    monkeypatch.setattr(reg._notio, "find_team_directory_by_name", fake_find_name)
    monkeypatch.setattr(reg._notio, "update_team_directory_ids", fake_update)
    
@pytest.mark.asyncio    
async def test_dispatch_unregister(tmp_path, monkeypatch):
    log = tmp_path / "dispatch_unregister_log.txt"
    payload = load_payload_example("!unregister Command Payload")
    payload["channelId"] = "123"
    log.write_text(f"Input: {payload}\n")

    lookup = load_notion_lookup()
    called = []

    async def fake_find(channel_id):
        return lookup

    async def fake_clear(page_id):
        called.append(page_id)
        return {"status": "ok"}

    monkeypatch.setattr(router._notio, "find_team_directory_by_channel", fake_find)
    monkeypatch.setattr(unregister_cmd._notio, "find_team_directory_by_channel", fake_find)
    monkeypatch.setattr(unregister_cmd._notio, "clear_team_directory_ids", fake_clear)

    with open(log, "a") as f:
        f.write("Step: dispatch\n")
    result = await router.dispatch(payload)
    with open(log, "a") as f:
        f.write(f"Output: {result}\n")
    assert result == {"output": "Готово. Тепер цей канал не зареєстрований ні на кого."}
    assert called == [lookup["results"][0]["id"]]


def test_parse_prefix_register(tmp_path):
    log = tmp_path / "parse_register_log.txt"
    payload = load_payload_example("!register Command Payload")
    message = payload["message"]
    log.write_text(f"Input: {message}\n")
    with open(log, "a") as f:
        f.write("Step: parse_prefix\n")
    result = router.parse_prefix(message)
    with open(log, "a") as f:
        f.write(f"Output: {result}\n")
    assert result == {"command": "register", "result": {"text": payload["result"]["text"]}}


def test_parse_prefix_unregister(tmp_path):
    log = tmp_path / "parse_unregister_log.txt"
    payload = load_payload_example("!unregister Command Payload")
    message = payload["message"]
    log.write_text(f"Input: {message}\n")
    with open(log, "a") as f:
        f.write("Step: parse_prefix\n")
    result = router.parse_prefix(message)
    with open(log, "a") as f:
        f.write(f"Output: {result}\n")
    assert result == {"command": "unregister", "result": {}}


@pytest.mark.asyncio
async def test_dispatch_connects(tmp_path, monkeypatch):
    log = tmp_path / "connects_log.txt"
    log.write_text("Input: connects\n")

    async def fake_lookup(channel_id):
        return load_notion_lookup()

    async def dummy(payload):
        return "ok"

    monkeypatch.setattr(router._notio, "find_team_directory_by_channel", fake_lookup)
    assert "connects_thisweek" in router.HANDLERS
    monkeypatch.setitem(router.HANDLERS, "connects_thisweek", dummy)

    payload = load_payload_example("/connects_thisweek Command Payload")
    payload["channelId"] = "123"
    payload["userId"] = "321"
    payload["sessionId"] = "123_321"

    with open(log, "a") as f:
        f.write("Step: dispatch\n")
    result = await router.dispatch(payload)
    with open(log, "a") as f:
        f.write(f"Output: {result}\n")
    assert result == {"output": "ok"}
