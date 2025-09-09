import json
import logging
import re
import sys
import types
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent

sys.path.append(str(ROOT))
sys.path.append(str(ROOT / "services"))

# Stub external google modules
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
# Create base logger and stub config modules
base_logger = logging.getLogger("discord_bot")

class DummyConfig:
    DATABASE_URL = ""
    NOTION_TEAM_DIRECTORY_DB_ID = ""
    NOTION_TOKEN = ""
    NOTION_WORKLOAD_DB_ID = ""
    NOTION_PROFILE_STATS_DB_ID = ""
    WEBHOOK_AUTH_TOKEN = ""
    SESSION_TTL = 1

config_mod = types.ModuleType("config")
config_mod.Config = DummyConfig
config_mod.logger = base_logger
config_mod.Strings = object()
sys.modules["config"] = config_mod

import router
from services.logging_utils import wrap_handler


@pytest.mark.asyncio
async def test_logging_success(tmp_path, monkeypatch, caplog):
    log_file = tmp_path / "logging_success.txt"
    log_file.write_text("Input: success\n")

    caplog.set_level(logging.DEBUG)

    async def fake_lookup(channel_id):
        return load_notion_lookup()

    async def dummy(payload):
        return "ok"

    monkeypatch.setattr(router._notio, "find_team_directory_by_channel", fake_lookup)
    router.HANDLERS["dummy"] = wrap_handler("dummy", dummy)

    payload = load_payload_example("Generic Slash Command Payload")
    payload.update({"command": "dummy", "result": {}})
    payload.update({"channelId": "123", "userId": "321", "sessionId": "123_321"})

    with open(log_file, "a") as f:
        f.write("Step: dispatch\n")
    result = await router.dispatch(payload)
    with open(log_file, "a") as f:
        f.write(f"Output: {result}\n")

    assert result == {"output": "ok"}
    assert any(r.message == "start" and r.step_name == "router.dispatch" for r in caplog.records)
    assert any(r.message == "done" and r.step_name == "router.dispatch" for r in caplog.records)
    assert any(r.message == "done" and r.step_name == "dummy" for r in caplog.records)
    assert any(r.session_id == "123_321" for r in caplog.records)
    assert any(r.user == "321" for r in caplog.records)
    assert any(r.channel == "123" for r in caplog.records)


@pytest.mark.asyncio
async def test_logging_error(tmp_path, monkeypatch, caplog):
    log_file = tmp_path / "logging_error.txt"
    log_file.write_text("Input: error\n")

    caplog.set_level(logging.DEBUG)

    async def fake_lookup(channel_id):
        return load_notion_lookup()

    async def boom(payload):
        raise ValueError("boom")

    monkeypatch.setattr(router._notio, "find_team_directory_by_channel", fake_lookup)
    router.HANDLERS["boom"] = wrap_handler("boom", boom)

    payload = load_payload_example("Generic Slash Command Payload")
    payload.update({"command": "boom", "result": {}})
    payload.update({"channelId": "123", "userId": "321", "sessionId": "123_321"})

    with open(log_file, "a") as f:
        f.write("Step: dispatch\n")
    result = await router.dispatch(payload)
    with open(log_file, "a") as f:
        f.write(f"Output: {result}\n")

    assert result == {"output": "Спробуй трохи піздніше. Я тут пораюсь по хаті."}
    assert any(r.message == "failed" and r.step_name == "boom" for r in caplog.records)
    assert any(r.session_id == "123_321" for r in caplog.records)
    assert any(r.user == "321" for r in caplog.records)
    assert any(r.channel == "123" for r in caplog.records)
