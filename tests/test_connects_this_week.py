import json
import re
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT))
sys.path.append(str(ROOT / "services" / "cmd"))

import connects_this_week

# Load payload examples and responses once
payload_text = (ROOT / "payload_examples.txt").read_text()
responses_text = (ROOT / "responses").read_text()

# Extract the connects_thisweek command payload
match = re.search(
    r"/connects_thisweek Command Payload\n\n```json\n(\{.*?\})\n```",
    payload_text,
    re.S,
)
COMMAND_PAYLOAD = json.loads(match.group(1))
# command in code uses underscores
COMMAND_PAYLOAD["command"] = "connects_this_week"

# Extract sample Notion page id and url from responses
page_id_match = re.search(r'"id":\s*"([0-9a-f-]{36})"', responses_text)
page_url_match = re.search(r"https://www.notion.so/[^\"]+", responses_text)
PAGE_ID = page_id_match.group(1)
PAGE_URL = page_url_match.group(0)
SAMPLE_PROFILE = {"results": [{"id": PAGE_ID, "url": PAGE_URL}]}


class DummySession:
    def __init__(self, should_fail=False):
        self.should_fail = should_fail
        self.post_calls = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass

    async def post(self, url, json):
        self.post_calls.append((url, json))
        if self.should_fail:
            raise Exception("post failed")


class FakeDB:
    def __init__(self, *_):
        self.upsert_step_calls = []

    async def upsert_step(self, session_id, step, completed):
        self.upsert_step_calls.append((session_id, step, completed))

    async def close(self):
        pass


@pytest.mark.asyncio
async def test_profile_exists(monkeypatch, tmp_path):
    log_file = tmp_path / "profile_exists_log.txt"
    log_file.write_text(f"Input: {COMMAND_PAYLOAD}\n")

    session = DummySession()
    monkeypatch.setattr(connects_this_week.aiohttp, "ClientSession", lambda: session)
    monkeypatch.setattr(connects_this_week, "Config", SimpleNamespace(DATABASE_URL="sqlite://"))

    fake_notion = SimpleNamespace(
        get_profile_stats_by_name=AsyncMock(return_value=SAMPLE_PROFILE),
        update_profile_stats_connects=AsyncMock(),
        close=AsyncMock(),
    )
    monkeypatch.setattr(connects_this_week, "NotionConnector", lambda: fake_notion)
    monkeypatch.setattr(connects_this_week, "SurveyStepsDB", FakeDB)

    result = await connects_this_week.handle(COMMAND_PAYLOAD)

    with open(log_file, "a") as f:
        f.write("Step: handle called\n")
        f.write(f"Output: {result}\n")

    expected = (
        "Записав! Upwork connects: залишилось "
        f"{COMMAND_PAYLOAD['result']['connects']} на цьому тиждні."
    )
    assert result == expected
    assert fake_notion.update_profile_stats_connects.called


@pytest.mark.asyncio
async def test_no_profile(monkeypatch, tmp_path):
    log_file = tmp_path / "no_profile_log.txt"
    log_file.write_text(f"Input: {COMMAND_PAYLOAD}\n")

    session = DummySession()
    monkeypatch.setattr(connects_this_week.aiohttp, "ClientSession", lambda: session)
    monkeypatch.setattr(connects_this_week, "Config", SimpleNamespace(DATABASE_URL="sqlite://"))

    fake_notion = SimpleNamespace(
        get_profile_stats_by_name=AsyncMock(return_value={"results": []}),
        update_profile_stats_connects=AsyncMock(),
        close=AsyncMock(),
    )
    monkeypatch.setattr(connects_this_week, "NotionConnector", lambda: fake_notion)
    monkeypatch.setattr(connects_this_week, "SurveyStepsDB", FakeDB)

    result = await connects_this_week.handle(COMMAND_PAYLOAD)

    with open(log_file, "a") as f:
        f.write("Step: handle called\n")
        f.write(f"Output: {result}\n")

    assert not fake_notion.update_profile_stats_connects.called


@pytest.mark.asyncio
async def test_database_error(monkeypatch, tmp_path):
    log_file = tmp_path / "db_error_log.txt"
    log_file.write_text(f"Input: {COMMAND_PAYLOAD}\n")

    session = DummySession(should_fail=True)
    monkeypatch.setattr(connects_this_week.aiohttp, "ClientSession", lambda: session)
    monkeypatch.setattr(connects_this_week, "Config", SimpleNamespace(DATABASE_URL="sqlite://"))

    fake_notion = SimpleNamespace(
        get_profile_stats_by_name=AsyncMock(return_value=SAMPLE_PROFILE),
        update_profile_stats_connects=AsyncMock(),
        close=AsyncMock(),
    )
    monkeypatch.setattr(connects_this_week, "NotionConnector", lambda: fake_notion)
    monkeypatch.setattr(connects_this_week, "SurveyStepsDB", FakeDB)

    result = await connects_this_week.handle(COMMAND_PAYLOAD)

    with open(log_file, "a") as f:
        f.write("Step: handle called\n")
        f.write(f"Output: {result}\n")

    assert result == connects_this_week.ERROR_MESSAGE


@pytest.mark.asyncio
async def test_end_to_end(monkeypatch, tmp_path):
    """Simulate slash command call end-to-end through handler."""
    log_file = tmp_path / "e2e_log.txt"
    log_file.write_text(f"Input: {COMMAND_PAYLOAD}\n")

    session = DummySession()
    monkeypatch.setattr(connects_this_week.aiohttp, "ClientSession", lambda: session)
    monkeypatch.setattr(connects_this_week, "Config", SimpleNamespace(DATABASE_URL="sqlite://"))

    fake_notion = SimpleNamespace(
        get_profile_stats_by_name=AsyncMock(return_value=SAMPLE_PROFILE),
        update_profile_stats_connects=AsyncMock(),
        close=AsyncMock(),
    )
    monkeypatch.setattr(connects_this_week, "NotionConnector", lambda: fake_notion)
    monkeypatch.setattr(connects_this_week, "SurveyStepsDB", FakeDB)

    result = await connects_this_week.handle(COMMAND_PAYLOAD.copy())

    with open(log_file, "a") as f:
        f.write("Step: handle called\n")
        f.write(f"Output: {result}\n")

    expected = (
        "Записав! Upwork connects: залишилось "
        f"{COMMAND_PAYLOAD['result']['connects']} на цьому тиждні."
    )
    assert result == expected
