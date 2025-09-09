import sys
import json
import re
from pathlib import Path
import types
import logging

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "services/cmd"))

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

import unregister


def load_payload_example(title: str) -> dict:
    text = (ROOT / "payload_examples.txt").read_text()
    start = text.index(title)
    match = re.search(r"```json\n(.*?)\n```", text[start:], re.DOTALL)
    return json.loads(match.group(1))


def load_notion_lookup() -> dict:
    text = (ROOT / "responses").read_text()
    name = re.search(r'plain_text": "([^"]+Lernichenko)"', text).group(1)
    todo_url = re.search(r"https://www.notion.so/[0-9a-f-]+", text).group(0)
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


@pytest.mark.asyncio
async def test_unregister_success(tmp_path, monkeypatch):
    log = tmp_path / "unregister_success_log.txt"
    payload = load_payload_example("!unregister Command Payload")
    log.write_text(f"Input: {payload}\n")

    lookup = load_notion_lookup()
    called = []

    async def fake_find(channel_id):
        return lookup

    async def fake_clear(page_id):
        called.append(page_id)
        return {"status": "ok"}

    monkeypatch.setattr(unregister._notio, "find_team_directory_by_channel", fake_find)
    monkeypatch.setattr(unregister._notio, "clear_team_directory_ids", fake_clear)

    with open(log, "a") as f:
        f.write("Step: handle\n")
    result = await unregister.handle(payload)
    with open(log, "a") as f:
        f.write(f"Output: {result}\n")

    assert result == "Готово. Тепер цей канал не зареєстрований ні на кого."
    assert called == [lookup["results"][0]["id"]]


@pytest.mark.asyncio
async def test_unregister_channel_missing(tmp_path, monkeypatch):
    log = tmp_path / "unregister_missing_log.txt"
    payload = load_payload_example("!unregister Command Payload")
    log.write_text(f"Input: {payload}\n")

    async def fake_find(channel_id):
        return {"results": []}

    monkeypatch.setattr(unregister._notio, "find_team_directory_by_channel", fake_find)

    with open(log, "a") as f:
        f.write("Step: handle\n")
    result = await unregister.handle(payload)
    with open(log, "a") as f:
        f.write(f"Output: {result}\n")

    assert (
        result
        == "Вибачте, але цей канал не зареєстрований ні на кого. Тому не можу зняти його з реєстрації"
    )


@pytest.mark.asyncio
async def test_unregister_notion_error(tmp_path, monkeypatch):
    log = tmp_path / "unregister_error_log.txt"
    payload = load_payload_example("!unregister Command Payload")
    log.write_text(f"Input: {payload}\n")

    lookup = load_notion_lookup()

    async def fake_find(channel_id):
        return lookup

    async def fake_clear(page_id):
        raise Exception("fail")

    monkeypatch.setattr(unregister._notio, "find_team_directory_by_channel", fake_find)
    monkeypatch.setattr(unregister._notio, "clear_team_directory_ids", fake_clear)

    with open(log, "a") as f:
        f.write("Step: handle\n")
    result = await unregister.handle(payload)
    with open(log, "a") as f:
        f.write(f"Output: {result}\n")

    assert result == "Спробуй трохи піздніше. Я тут пораюсь по хаті."

