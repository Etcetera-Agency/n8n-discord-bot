import json
import re
import sys
import types
import importlib
from pathlib import Path

import pytest
from databases import Database

ROOT = Path(__file__).resolve().parent.parent
SERVICES = ROOT / "services"
sys.path.append(str(ROOT))
sys.path.append(str(SERVICES))

# Stub the services package to avoid side effects from __init__
# Stub the services and services.cmd packages to bypass their __init__ modules
services_pkg = types.ModuleType("services")
services_pkg.__path__ = [str(SERVICES)]
sys.modules.setdefault("services", services_pkg)

cmd_pkg = types.ModuleType("services.cmd")
cmd_pkg.__path__ = [str(SERVICES / "cmd")]
sys.modules.setdefault("services.cmd", cmd_pkg)

# Load required modules manually
spec_db = importlib.util.spec_from_file_location(
    "services.survey_steps_db", SERVICES / "survey_steps_db.py"
)
survey_steps_db = importlib.util.module_from_spec(spec_db)
spec_db.loader.exec_module(survey_steps_db)
sys.modules["services.survey_steps_db"] = survey_steps_db
SurveyStepsDB = survey_steps_db.SurveyStepsDB

spec_cc = importlib.util.spec_from_file_location(
    "services.cmd.check_channel", SERVICES / "cmd" / "check_channel.py"
)
check_channel = importlib.util.module_from_spec(spec_cc)
spec_cc.loader.exec_module(check_channel)
sys.modules["services.cmd.check_channel"] = check_channel

spec_router = importlib.util.spec_from_file_location(
    "services.router", SERVICES / "router.py"
)
router = importlib.util.module_from_spec(spec_router)
spec_router.loader.exec_module(router)
sys.modules["services.router"] = router


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


def log_step(log: Path, message: str) -> None:
    with open(log, "a") as f:
        f.write(f"{message}\n")


text = Path(ROOT / "payload_examples.txt").read_text()
SURVEY_FLOW = re.findall(r"\"stepName\": \"([^\"]+)\"", text)


@pytest.mark.asyncio
async def test_handle_no_pending_steps(tmp_path):
    log = tmp_path / "no_pending_log.txt"
    payload = load_payload_example("check_channel Command Payload")
    payload.update({"channelId": "CHAN", "userId": "USER", "sessionId": "CHAN_USER"})
    payload["channelName"] = load_sample_name()
    log.write_text(f"Input: {payload}\n")

    db_url = f"sqlite+aiosqlite:///{tmp_path}/test.db"
    database = Database(db_url)
    log_step(log, "DB connect")
    await database.connect()
    await database.execute(CREATE_TABLE)
    log_step(log, "DB setup")
    repo = SurveyStepsDB(db_url, db=database)
    await repo.upsert_step("CHAN", SURVEY_FLOW[0], True)

    log_step(log, "Call handle")
    result = await check_channel.handle(payload, repo)
    log_step(log, f"Output: {result}")
    assert result == {"output": True, "steps": []}

    await database.disconnect()
    log_step(log, "DB disconnect")


@pytest.mark.asyncio
async def test_handle_pending_steps(tmp_path):
    log = tmp_path / "pending_log.txt"
    payload = load_payload_example("check_channel Command Payload")
    payload.update({"channelId": "CHAN", "userId": "USER", "sessionId": "CHAN_USER"})
    payload["channelName"] = load_sample_name()
    log.write_text(f"Input: {payload}\n")

    db_url = f"sqlite+aiosqlite:///{tmp_path}/test.db"
    database = Database(db_url)
    log_step(log, "DB connect")
    await database.connect()
    await database.execute(CREATE_TABLE)
    log_step(log, "DB setup")
    repo = SurveyStepsDB(db_url, db=database)
    await repo.upsert_step("CHAN", SURVEY_FLOW[0], False)

    log_step(log, "Call handle")
    result = await check_channel.handle(payload, repo)
    log_step(log, f"Output: {result}")
    assert result == {"output": True, "steps": [SURVEY_FLOW[0]]}

    await database.disconnect()
    log_step(log, "DB disconnect")


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

    log_step(log, "Call handle")
    result = await check_channel.handle(payload, repo)
    log_step(log, f"Output: {result}")
    assert result == {
        "output": False,
        "message": "Спробуй трохи піздніше. Я тут пораюсь по хаті.",
    }


@pytest.mark.asyncio
async def test_dispatch_check_channel(tmp_path, monkeypatch):
    log = tmp_path / "dispatch_log.txt"
    payload = load_payload_example("check_channel Command Payload")
    payload.update({"channelId": "CHAN", "userId": "USER", "sessionId": "CHAN_USER"})
    payload["channelName"] = load_sample_name()
    log.write_text(f"Input: {payload}\n")

    db_url = f"sqlite+aiosqlite:///{tmp_path}/test.db"
    database = Database(db_url)
    log_step(log, "DB connect")
    await database.connect()
    await database.execute(CREATE_TABLE)
    log_step(log, "DB setup")
    repo = SurveyStepsDB(db_url, db=database)
    await repo.upsert_step("CHAN", SURVEY_FLOW[0], False)
    await database.disconnect()
    log_step(log, "DB disconnect")

    monkeypatch.setattr(check_channel.Config, "DATABASE_URL", db_url, raising=False)

    async def fake_lookup(channel_id):
        return {
            "results": [
                {"discord_id": payload["userId"], "name": load_sample_name(), "to_do": None}
            ]
        }

    monkeypatch.setattr(router._notio, "find_team_directory_by_channel", fake_lookup)

    log_step(log, "Dispatch")
    result = await router.dispatch(payload)
    log_step(log, f"Output: {result}")
    assert result == {"output": {"output": True, "steps": [SURVEY_FLOW[0]]}}
