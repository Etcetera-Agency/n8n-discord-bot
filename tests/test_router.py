import sys
from pathlib import Path
import pytest
import types
import logging

ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT))
sys.path.append(str(ROOT / "services"))
# Stub config to avoid heavy imports
class DummyConfig:
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

import router

survey_manager = router.survey_manager


@pytest.mark.asyncio
async def test_dispatch_mention(tmp_path, monkeypatch):
    log = tmp_path / "mention_log.txt"
    log.write_text("Input: mention\n")

    async def fake_lookup(channel_id):
        return {"results": [{"name": "User", "discord_id": "321", "channel_id": "123", "to_do": "http://todo"}]}

    monkeypatch.setattr(router._notio, "find_team_directory_by_channel", fake_lookup)
    payload = {"type": "mention", "message": "hi", "channelId": "123", "result": {}, "userId": "321"}
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
        return {"results": [{"name": "User", "discord_id": "321", "channel_id": "", "to_do": "http://todo"}]}

    async def dummy(payload):
        return "ok"

    monkeypatch.setattr(router._notio, "find_team_directory_by_channel", fake_lookup)
    monkeypatch.setitem(router.HANDLERS, "dummy", dummy)
    payload = {"command": "dummy", "channelId": "123", "userId": "u", "result": {}, "type": "command"}
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
        return {"results": [{"name": "User", "discord_id": "321", "channel_id": "", "to_do": "http://todo"}]}

    async def step1(payload):
        return "done"

    monkeypatch.setattr(router._notio, "find_team_directory_by_channel", fake_lookup)
    monkeypatch.setitem(router.HANDLERS, "step1", step1)
    survey_manager.create_survey("321", "123", ["step1"], "sess")
    payload = {
        "command": "survey",
        "channelId": "123",
        "userId": "321",
        "type": "command",
        "result": {"stepName": "step1", "value": "v"},
    }
    with open(log, "a") as f:
        f.write("Step: dispatch\n")
    result = await router.dispatch(payload)
    with open(log, "a") as f:
        f.write(f"Output: {result}\n")
    assert result == {
        "output": "done",
        "survey": "end",
        "url": "http://todo",
    }
    assert survey_manager.get_survey("123") is None


@pytest.mark.asyncio
async def test_dispatch_survey_continue(tmp_path, monkeypatch):
    log = tmp_path / "survey_continue_log.txt"
    log.write_text("Input: survey-continue\n")

    async def fake_lookup(channel_id):
        return {"results": [{"name": "User", "discord_id": "321", "channel_id": "", "to_do": "http://todo"}]}

    async def step1(payload):
        return "step1"

    async def step2(payload):
        return "step2"

    monkeypatch.setattr(router._notio, "find_team_directory_by_channel", fake_lookup)
    monkeypatch.setitem(router.HANDLERS, "step1", step1)
    monkeypatch.setitem(router.HANDLERS, "step2", step2)
    survey_manager.create_survey("321", "123", ["step1", "step2"], "sess")
    payload = {
        "command": "survey",
        "channelId": "123",
        "userId": "321",
        "type": "command",
        "result": {"stepName": "step1", "value": "v"},
    }
    with open(log, "a") as f:
        f.write("Step: dispatch\n")
    result = await router.dispatch(payload)
    with open(log, "a") as f:
        f.write(f"Output: {result}\n")
    assert result == {"output": "step1", "survey": "continue", "next_step": "step2"}
    assert survey_manager.get_survey("123") is not None
