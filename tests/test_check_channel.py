import json
import re
import sys
from pathlib import Path

import pytest
from databases import Database

ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT))
sys.path.append(str(ROOT / "services"))

text = Path(ROOT / "payload_examples.txt").read_text()
SURVEY_FLOW = re.findall(r"\"stepName\": \"([^\"]+)\"", text)

from services.survey_steps_db import SurveyStepsDB
from services.cmd.check_channel import handle


def load_payload_example(title: str) -> dict:
    text = Path(ROOT / "payload_examples.txt").read_text()
    start = text.index(title)
    segment = text[start:]
    match = re.search(r"```json\n(.*?)(?:\n```|\n## )", segment, re.DOTALL)
    return json.loads(match.group(1))


def load_sample_name() -> str:
    text = Path(ROOT / "responses").read_text()
    return re.search(r'plain_text": "([^"]+)"', text).group(1)


CREATE_TABLE = (
    "CREATE TABLE IF NOT EXISTS n8n_survey_steps_missed ("
    "id INTEGER PRIMARY KEY AUTOINCREMENT,"
    "session_id TEXT NOT NULL,"
    "step_name TEXT NOT NULL,"
    "completed BOOLEAN NOT NULL,"
    "updated TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,"
    "UNIQUE(session_id, step_name)"
    ")"
)


@pytest.mark.asyncio
async def test_handle_no_pending_steps(tmp_path):
    log = tmp_path / "no_pending_log.txt"
    payload = load_payload_example("check_channel Command Payload")
    payload.update({"channelId": "CHAN", "userId": "USER", "sessionId": "CHAN_USER"})
    payload["channelName"] = load_sample_name()
    log.write_text(f"Input: {payload}\n")

    db_url = f"sqlite+aiosqlite:///{tmp_path}/test.db"
    database = Database(db_url)
    await database.connect()
    await database.execute(CREATE_TABLE)
    repo = SurveyStepsDB(db_url, db=database)
    await repo.upsert_step("CHAN", SURVEY_FLOW[0], True)

    result = await handle(payload, repo)
    with open(log, "a") as f:
        f.write("Step: handle\n")
        f.write(f"Output: {result}\n")

    assert result == {"output": True, "steps": []}
    await database.disconnect()


@pytest.mark.asyncio
async def test_handle_pending_steps(tmp_path):
    log = tmp_path / "pending_log.txt"
    payload = load_payload_example("check_channel Command Payload")
    payload.update({"channelId": "CHAN", "userId": "USER", "sessionId": "CHAN_USER"})
    payload["channelName"] = load_sample_name()
    log.write_text(f"Input: {payload}\n")

    db_url = f"sqlite+aiosqlite:///{tmp_path}/test.db"
    database = Database(db_url)
    await database.connect()
    await database.execute(CREATE_TABLE)
    repo = SurveyStepsDB(db_url, db=database)
    await repo.upsert_step("CHAN", SURVEY_FLOW[0], False)

    result = await handle(payload, repo)
    with open(log, "a") as f:
        f.write("Step: handle\n")
        f.write(f"Output: {result}\n")

    assert result == {"output": True, "steps": [SURVEY_FLOW[0]]}
    await database.disconnect()


@pytest.mark.asyncio
async def test_handle_db_failure(tmp_path, monkeypatch):
    log = tmp_path / "db_failure_log.txt"
    payload = load_payload_example("check_channel Command Payload")
    payload.update({"channelId": "CHAN", "userId": "USER", "sessionId": "CHAN_USER"})
    payload["channelName"] = load_sample_name()
    log.write_text(f"Input: {payload}\n")

    async def boom(*args, **kwargs):
        raise RuntimeError("db down")

    monkeypatch.setattr(SurveyStepsDB, "fetch_week", boom)
    repo = SurveyStepsDB("sqlite:///:memory:")

    result = await handle(payload, repo)
    with open(log, "a") as f:
        f.write("Step: handle\n")
        f.write(f"Output: {result}\n")

    assert result == "Спробуй трохи піздніше. Я тут пораюсь по хаті."
