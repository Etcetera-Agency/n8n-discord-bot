import json
import re
import sys
import types
import logging
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT))
sys.path.append(str(ROOT / "services"))


class DummyConfig:
    NOTION_TEAM_DIRECTORY_DB_ID = ""
    NOTION_TOKEN = ""
    NOTION_WORKLOAD_DB_ID = ""
    NOTION_PROFILE_STATS_DB_ID = ""
    N8N_WEBHOOK_URL = ""
    WEBHOOK_AUTH_TOKEN = ""
    SESSION_TTL = 1
    DATABASE_URL = "sqlite:///test.db"


sys.modules["config"] = types.SimpleNamespace(
    Config=DummyConfig, logger=logging.getLogger("test"), Strings=object()
)

import router
from services.cmd import workload_nextweek


def load_payload_example(title: str) -> dict:
    text = Path(ROOT / "payload_examples.txt").read_text()
    start = text.index(title)
    match = re.search(r"```json\n(.*?)\n```", text[start:], re.DOTALL)
    return json.loads(match.group(1))


def load_workload_page() -> dict:
    text = Path(ROOT / "responses").read_text()
    start = text.index("here is example page for Workload DB.")
    match = re.search(r"\[(\s|.)*?\n\]", text[start:], re.DOTALL)
    return {"results": json.loads(match.group(0))}


def load_notion_lookup() -> dict:
    text = Path(ROOT / "responses").read_text()
    name = re.search(r'plain_text\": \"([^\"]+Lernichenko)\"', text).group(1)
    todo_url = re.search(r'https://www.notion.so/[0-9a-f-]+', text).group(0)
    return {"results": [{"name": name, "discord_id": "321", "channel_id": "123", "to_do": todo_url}]}


@pytest.mark.asyncio
async def test_handle_valid_write(monkeypatch, tmp_path):
    payload = load_payload_example("Workload Slash Command Payload (e.g., /workload_today)")
    payload["command"] = "workload_nextweek"
    log_file = tmp_path / "valid_write_log.txt"
    log_file.write_text(f"Input: {payload}\n")

    page = load_workload_page()["results"][0]

    async def fake_get(name):
        return {"results": [page]}

    update_mock = AsyncMock()
    monkeypatch.setattr(
        workload_nextweek,
        "_notion",
        types.SimpleNamespace(
            get_workload_page_by_name=fake_get,
            update_workload_day=update_mock,
        ),
    )
    steps_mock = AsyncMock()
    monkeypatch.setattr(
        workload_nextweek,
        "_steps",
        types.SimpleNamespace(upsert_step=steps_mock),
    )

    result = await workload_nextweek.handle(payload)
    with open(log_file, "a") as f:
        f.write("Step: handle\n")
        f.write(f"Output: {result}\n")

    update_mock.assert_awaited_with(
        page["id"], "Next week plan", payload["result"]["value"]
    )
    steps_mock.assert_awaited_with(payload["channelId"], "workload_nextweek", True)
    assert result == workload_nextweek.template(payload["result"]["value"])


@pytest.mark.asyncio
async def test_handle_notion_failure(monkeypatch, tmp_path):
    payload = load_payload_example("Workload Slash Command Payload (e.g., /workload_today)")
    payload["command"] = "workload_nextweek"
    log_file = tmp_path / "failure_log.txt"
    log_file.write_text(f"Input: {payload}\n")

    page = load_workload_page()["results"][0]

    async def fake_get(name):
        return {"results": [page]}

    async def fake_update(*args, **kwargs):
        raise Exception("boom")

    monkeypatch.setattr(
        workload_nextweek,
        "_notion",
        types.SimpleNamespace(
            get_workload_page_by_name=fake_get,
            update_workload_day=fake_update,
        ),
    )
    monkeypatch.setattr(
        workload_nextweek,
        "_steps",
        types.SimpleNamespace(upsert_step=AsyncMock()),
    )

    result = await workload_nextweek.handle(payload)
    with open(log_file, "a") as f:
        f.write("Step: handle error\n")
        f.write(f"Output: {result}\n")

    assert result == "Спробуй трохи піздніше. Я тут пораюсь по хаті."


@pytest.mark.asyncio
async def test_handle_user_not_found(monkeypatch, tmp_path):
    payload = load_payload_example("Workload Slash Command Payload (e.g., /workload_today)")
    payload["command"] = "workload_nextweek"
    log_file = tmp_path / "user_not_found_log.txt"
    log_file.write_text(f"Input: {payload}\n")

    async def fake_get(name):
        return {"results": []}

    update_mock = AsyncMock()
    steps_mock = AsyncMock()
    monkeypatch.setattr(
        workload_nextweek,
        "_notion",
        types.SimpleNamespace(
            get_workload_page_by_name=fake_get,
            update_workload_day=update_mock,
        ),
    )
    monkeypatch.setattr(
        workload_nextweek,
        "_steps",
        types.SimpleNamespace(upsert_step=steps_mock),
    )

    result = await workload_nextweek.handle(payload)
    with open(log_file, "a") as f:
        f.write("Step: handle missing user\n")
        f.write(f"Output: {result}\n")

    update_mock.assert_not_awaited()
    steps_mock.assert_not_awaited()
    assert result == "Спробуй трохи піздніше. Я тут пораюсь по хаті."


@pytest.mark.asyncio
async def test_workload_nextweek_e2e(monkeypatch, tmp_path):
    payload = load_payload_example("Workload Slash Command Payload (e.g., /workload_today)")
    payload["command"] = "workload_nextweek"
    log_file = tmp_path / "e2e_log.txt"
    log_file.write_text(f"Input: {payload}\n")

    lookup = load_notion_lookup()
    lookup["results"][0]["discord_id"] = payload["userId"]
    lookup["results"][0]["channel_id"] = payload["channelId"]

    async def fake_lookup(cid):
        return lookup

    monkeypatch.setattr(router._notio, "find_team_directory_by_channel", fake_lookup)

    page = load_workload_page()

    async def fake_get(name):
        return page

    async def fake_update(*args, **kwargs):
        return {"status": "ok"}

    monkeypatch.setattr(
        workload_nextweek,
        "_notion",
        types.SimpleNamespace(
            get_workload_page_by_name=fake_get,
            update_workload_day=fake_update,
        ),
    )
    monkeypatch.setattr(
        workload_nextweek,
        "_steps",
        types.SimpleNamespace(upsert_step=AsyncMock()),
    )

    result = await router.dispatch(payload)
    with open(log_file, "a") as f:
        f.write("Step: dispatch\n")
        f.write(f"Output: {result}\n")

    expected = workload_nextweek.template(payload["result"]["value"])
    assert result == {"output": expected}

