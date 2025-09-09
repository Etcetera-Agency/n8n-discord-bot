import json
import re
from pathlib import Path

import pytest

from services.cmd import register


ROOT = Path(__file__).resolve().parent.parent


def load_payload_example(title: str) -> dict:
    text = Path(ROOT / "payload_examples.txt").read_text()
    start = text.index(title)
    match = re.search(r"```json\n(.*?)\n```", text[start:], re.DOTALL)
    return json.loads(match.group(1))


def load_notion_page() -> dict:
    text = Path(ROOT / "responses").read_text()
    name = re.search(r'plain_text": "([^"]+Lernichenko)"', text).group(1)
    url = re.search(r"https://www.notion.so/[0-9a-f-]+", text).group(0)
    return {
        "results": [
            {
                "id": "abc",
                "url": url,
                "name": name,
                "discord_id": "other",
                "channel_id": "1234567890",
                "to_do": url,
            }
        ]
    }


@pytest.mark.asyncio
async def test_handle_register_channel_free(tmp_path, monkeypatch):
    log = tmp_path / "channel_free_log.txt"
    payload = load_payload_example("!register Command Payload")
    payload["userId"] = "321"
    payload["channelId"] = "123"
    log.write_text(f"Input: {payload}\n")

    async def fake_find_channel(cid):
        return {"results": []}

    async def fake_find_name(name):
        return {"results": []}

    async def fake_create(name, uid, cid):
        fake_create.called = True
        return {"url": "https://www.notion.so/new"}

    fake_create.called = False
    monkeypatch.setattr(register._notio, "find_team_directory_by_channel", fake_find_channel)
    monkeypatch.setattr(register._notio, "find_team_directory_by_name", fake_find_name)
    monkeypatch.setattr(register._notio, "create_team_directory_page", fake_create)

    with open(log, "a") as f:
        f.write("Step: handle\n")
    result = await register.handle(payload)
    with open(log, "a") as f:
        f.write(f"Output: {result}\n")
    assert fake_create.called is True
    assert result == "Канал успішно зареєстровано на User Name"


@pytest.mark.asyncio
async def test_handle_register_channel_taken(tmp_path, monkeypatch):
    log = tmp_path / "channel_taken_log.txt"
    payload = load_payload_example("!register Command Payload")
    payload["userId"] = "321"
    payload["channelId"] = "123"
    log.write_text(f"Input: {payload}\n")

    async def fake_find_channel(cid):
        return load_notion_page()

    monkeypatch.setattr(register._notio, "find_team_directory_by_channel", fake_find_channel)

    with open(log, "a") as f:
        f.write("Step: handle\n")
    result = await register.handle(payload)
    with open(log, "a") as f:
        f.write(f"Output: {result}\n")
    assert result == "Канал вже зареєстрований на когось іншого."


@pytest.mark.asyncio
async def test_handle_register_error(tmp_path, monkeypatch):
    log = tmp_path / "register_error_log.txt"
    payload = load_payload_example("!register Command Payload")
    payload["userId"] = "321"
    payload["channelId"] = "123"
    log.write_text(f"Input: {payload}\n")

    async def fake_find_channel(cid):
        return {"results": []}

    async def fake_find_name(name):
        return {"results": []}

    async def fake_create(name, uid, cid):
        raise Exception("boom")

    monkeypatch.setattr(register._notio, "find_team_directory_by_channel", fake_find_channel)
    monkeypatch.setattr(register._notio, "find_team_directory_by_name", fake_find_name)
    monkeypatch.setattr(register._notio, "create_team_directory_page", fake_create)

    with open(log, "a") as f:
        f.write("Step: handle\n")
    result = await register.handle(payload)
    with open(log, "a") as f:
        f.write(f"Output: {result}\n")
    assert result == "Спробуй трохи піздніше. Я тут пораюсь по хаті."

