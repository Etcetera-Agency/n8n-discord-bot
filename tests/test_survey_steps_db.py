import sys
from pathlib import Path
from datetime import datetime, timedelta

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT / "services"))

from survey_steps_db import SurveyStepsDB
from databases import Database

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

CREATE_TABLE_NO_UNIQUE = (
    "CREATE TABLE IF NOT EXISTS n8n_survey_steps_missed ("
    "id INTEGER PRIMARY KEY AUTOINCREMENT,"
    "session_id TEXT NOT NULL,"
    "step_name TEXT NOT NULL,"
    "completed BOOLEAN NOT NULL,"
    "updated TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP"
    ")"
)


def week_start_str():
    return (datetime.utcnow() - timedelta(days=1)).replace(microsecond=0).isoformat(" ")


@pytest.mark.asyncio
async def test_upsert_and_fetch_week(tmp_path):
    log_file = tmp_path / "upsert_fetch_log.txt"
    log_file.write_text("Input: session=S1, step=workload_today, completed=True\n")

    db_url = f"sqlite+aiosqlite:///{tmp_path}/test.db"
    database = Database(db_url)
    await database.connect()
    await database.execute(CREATE_TABLE)
    repo = SurveyStepsDB(db_url, db=database)

    await repo.upsert_step("S1", "workload_today", True)
    records = await repo.fetch_week("S1", week_start_str())
    with open(log_file, "a") as f:
        f.write("Step: upsert and fetch\n")
        f.write(f"Output: {records}\n")

    assert records and records[0]["step_name"] == "workload_today"
    assert bool(records[0]["completed"]) is True

    await database.disconnect()


@pytest.mark.asyncio
async def test_upsert_updates_existing(tmp_path):
    log_file = tmp_path / "upsert_update_log.txt"
    log_file.write_text("Input: session=S1, step=connects_thisweek, completed False->True\n")

    db_url = f"sqlite+aiosqlite:///{tmp_path}/test.db"
    database = Database(db_url)
    await database.connect()
    await database.execute(CREATE_TABLE)
    repo = SurveyStepsDB(db_url, db=database)

    await repo.upsert_step("S1", "connects_thisweek", False)
    await repo.upsert_step("S1", "connects_thisweek", True)
    records = await repo.fetch_week("S1", week_start_str())
    with open(log_file, "a") as f:
        f.write("Step: upsert twice and fetch\n")
        f.write(f"Output: {records}\n")

    assert records and bool(records[0]["completed"]) is True

    await database.disconnect()


@pytest.mark.asyncio
async def test_pending_steps(tmp_path):
    log_file = tmp_path / "pending_steps_log.txt"
    log_file.write_text("Input: session=S1, steps workload_today/connects_thisweek/workload_nextweek\n")

    db_url = f"sqlite+aiosqlite:///{tmp_path}/test.db"
    database = Database(db_url)
    await database.connect()
    await database.execute(CREATE_TABLE)
    repo = SurveyStepsDB(db_url, db=database)

    await repo.upsert_step("S1", "workload_today", True)
    await repo.upsert_step("S1", "connects_thisweek", False)
    pending = await repo.pending_steps(
        "S1", week_start_str(), ["workload_today", "connects_thisweek", "workload_nextweek"]
    )
    with open(log_file, "a") as f:
        f.write("Step: compute pending steps\n")
        f.write(f"Output: {pending}\n")

    assert pending == ["connects_thisweek", "workload_nextweek"]

    await database.disconnect()


@pytest.mark.asyncio
async def test_fetch_week_returns_latest(tmp_path):
    log_file = tmp_path / "fetch_week_latest_log.txt"
    log_file.write_text(
        "Input: session=S1, step=workload_today, statuses False then True\n"
    )

    db_url = f"sqlite+aiosqlite:///{tmp_path}/test.db"
    database = Database(db_url)
    await database.connect()
    await database.execute(CREATE_TABLE_NO_UNIQUE)
    repo = SurveyStepsDB(db_url, db=database)

    week_start = datetime.utcnow() - timedelta(days=1)
    week_start_str = week_start.replace(microsecond=0).isoformat(" ")
    first = (week_start + timedelta(hours=1)).isoformat(" ")
    second = (week_start + timedelta(hours=2)).isoformat(" ")

    await database.execute(
        "INSERT INTO n8n_survey_steps_missed (session_id, step_name, completed, updated)"
        " VALUES (:session_id, :step_name, :completed, :updated)",
        {"session_id": "S1", "step_name": "workload_today", "completed": False, "updated": first},
    )
    await database.execute(
        "INSERT INTO n8n_survey_steps_missed (session_id, step_name, completed, updated)"
        " VALUES (:session_id, :step_name, :completed, :updated)",
        {"session_id": "S1", "step_name": "workload_today", "completed": True, "updated": second},
    )

    records = await repo.fetch_week("S1", week_start_str)
    with open(log_file, "a") as f:
        f.write("Step: insert duplicates and fetch\n")
        f.write(f"Output: {records}\n")

    assert len(records) == 1
    assert bool(records[0]["completed"]) is True

    await database.disconnect()

