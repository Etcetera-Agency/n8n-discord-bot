import sys
import json
import re
import types
from pathlib import Path
from datetime import datetime, timezone

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT))
sys.path.append(str(ROOT / "services"))

import router
from services.cmd import workload_today
from services.notion_connector import NotionError


def load_payload_example(title: str) -> dict:
    text = (ROOT / "payload_examples.txt").read_text()
    start = text.index(title)
    match = re.search(r"```json\n(.*?)\n```", text[start:], re.DOTALL)
    return json.loads(match.group(1))


def load_workload_response() -> dict:
    text = (ROOT / "responses").read_text()
    page_id = re.search(r'"id": "([0-9a-f-]{36})"', text).group(1)
    url_pattern = r'"url": "(https://www.notion.so/[^"%]*{}[^"]*)"'.format(
        page_id.replace('-', '')
    )
    url = re.search(url_pattern, text).group(1)
    capacity = int(re.search(r'"Capacity": {[^}]*"number": ([0-9]+)', text).group(1))
    mon_fact = float(re.search(r'"Mon Fact": {[^}]*"number": ([0-9.]+)', text).group(1))
    tue_fact = float(re.search(r'"Tue Fact": {[^}]*"number": ([0-9.]+)', text).group(1))
    wed_fact = float(re.search(r'"Wed Fact": {[^}]*"number": ([0-9.]+)', text).group(1))
    return {
        "status": "ok",
        "results": [
            {
                "id": page_id,
                "url": url,
                "capacity": capacity,
                "fact_0": mon_fact,
                "fact_1": tue_fact,
                "fact_2": wed_fact,
            }
        ],
    }


@pytest.mark.asyncio
@pytest.mark.parametrize("hours_key", ["value", "workload"])
async def test_handle_workload_today_success(tmp_path, monkeypatch, hours_key):
    payload = load_payload_example("Workload Slash Command Payload")
    payload.update({"channelId": "123", "author": "Tester"})
    value = payload["result"]["value"]
    payload["result"] = {hours_key: value}
    log = tmp_path / "workload_today_success.txt"
    log.write_text(f"Input: {payload}\n")

    resp = load_workload_response()

    async def fake_query(db_id, flt, mapping):
        return resp

    called = {}

    async def fake_update(page_id, day_field, hours):
        called["page_id"] = page_id
        called["day_field"] = day_field
        called["hours"] = hours
        return {"status": "ok"}

    async def fake_upsert(session_id, step, completed):
        called["db"] = (session_id, step, completed)

    monkeypatch.setattr(workload_today._notio, "query_database", fake_query)
    monkeypatch.setattr(workload_today._notio, "update_workload_day", fake_update)
    monkeypatch.setattr(
        workload_today, "_steps_db", types.SimpleNamespace(upsert_step=fake_upsert)
    )

    result = await workload_today.handle(payload)

    with open(log, "a") as f:
        f.write("Step: handle\n")
        f.write(f"Output: {result}\n")

    dt = datetime.fromtimestamp(payload["timestamp"], timezone.utc)
    idx = dt.weekday()
    day_short = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"][idx]
    day_field = f"{day_short} Plan"
    assert called["day_field"] == day_field
    assert called["hours"] == int(value)
    assert called["db"] == (payload["channelId"], "workload_today", True)

    day_acc = [
        "понеділок",
        "вівторок",
        "середу",
        "четвер",
        "п'ятницю",
        "суботу",
        "неділю",
    ][idx]
    day_gen = [
        "понеділка",
        "вівторка",
        "середи",
        "четверга",
        "п'ятниці",
        "суботи",
        "неділі",
    ][idx]
    fact = int(
        resp["results"][0]["fact_0"]
        + resp["results"][0]["fact_1"]
        + resp["results"][0]["fact_2"]
    )
    capacity = int(resp["results"][0]["capacity"])
    hours = int(value)
    expected = (
        "Записав! \n"
        f"Заплановане навантаження у {day_acc}: {hours} год. \n"
        f"В щоденнику з понеділка до {day_gen}: {fact} год.\n"
        f"Капасіті на цей тиждень: {capacity} год."
    )
    assert result == expected


@pytest.mark.asyncio
async def test_handle_workload_today_error(tmp_path, monkeypatch):
    payload = load_payload_example("Workload Slash Command Payload")
    payload.update({"channelId": "123", "author": "Tester"})
    log = tmp_path / "workload_today_error.txt"
    log.write_text(f"Input: {payload}\n")

    resp = load_workload_response()

    async def fake_query(db_id, flt, mapping):
        return resp

    async def fake_update(*args, **kwargs):
        raise NotionError("boom")

    monkeypatch.setattr(workload_today._notio, "query_database", fake_query)
    monkeypatch.setattr(workload_today._notio, "update_workload_day", fake_update)
    monkeypatch.setattr(
        workload_today,
        "_steps_db",
        types.SimpleNamespace(upsert_step=lambda *a, **k: None),
    )
    monkeypatch.setattr(
        workload_today,
        "Config",
        types.SimpleNamespace(DATABASE_URL="sqlite://", NOTION_WORKLOAD_DB_ID="db"),
    )

    result = await workload_today.handle(payload)

    with open(log, "a") as f:
        f.write("Step: handle\n")
        f.write(f"Output: {result}\n")

    assert result == "Спробуй трохи піздніше. Я тут пораюсь по хаті."


@pytest.mark.asyncio
async def test_handle_workload_today_user_not_found(tmp_path, monkeypatch):
    payload = load_payload_example("Workload Slash Command Payload")
    payload.update({"channelId": "123", "author": "Tester"})
    log = tmp_path / "workload_today_not_found.txt"
    log.write_text(f"Input: {payload}\n")

    async def fake_query(db_id, flt, mapping):
        return {"status": "ok", "results": []}

    monkeypatch.setattr(workload_today._notio, "query_database", fake_query)
    monkeypatch.setattr(
        workload_today._notio, "update_workload_day", lambda *a, **k: None
    )
    monkeypatch.setattr(
        workload_today,
        "_steps_db",
        types.SimpleNamespace(upsert_step=lambda *a, **k: None),
    )
    monkeypatch.setattr(
        workload_today,
        "Config",
        types.SimpleNamespace(DATABASE_URL="sqlite://", NOTION_WORKLOAD_DB_ID="db"),
    )

    result = await workload_today.handle(payload)

    with open(log, "a") as f:
        f.write("Step: handle\n")
        f.write(f"Output: {result}\n")

    assert result == "Спробуй трохи піздніше. Я тут пораюсь по хаті."


@pytest.mark.asyncio
@pytest.mark.parametrize("hours_key", ["value", "workload"])
async def test_workload_today_e2e(tmp_path, monkeypatch, hours_key):
    payload = load_payload_example("Workload Slash Command Payload")
    payload.update({"userId": "321", "channelId": "123", "sessionId": "123_321"})
    value = payload["result"]["value"]
    payload["result"] = {hours_key: value}
    log = tmp_path / "workload_today_e2e.txt"
    log.write_text(f"Input: {payload}\n")

    def load_lookup():
        text = (ROOT / "responses").read_text()
        name = re.search(r'plain_text": "([^"]+Lernichenko)"', text).group(1)
        todo_url = re.search(r'https://www.notion.so/[0-9a-f-]+', text).group(0)
        return {
            "results": [
                {
                    "name": name,
                    "discord_id": "321",
                    "channel_id": "123",
                    "to_do": todo_url,
                }
            ]
        }

    async def fake_lookup(channel_id):
        return load_lookup()

    resp = load_workload_response()

    async def fake_query(db_id, flt, mapping):
        return resp

    async def fake_update(page_id, day_field, hours):
        return {"status": "ok"}

    async def fake_upsert(*a, **k):
        return None

    monkeypatch.setattr(router._notio, "find_team_directory_by_channel", fake_lookup)
    monkeypatch.setattr(workload_today._notio, "query_database", fake_query)
    monkeypatch.setattr(workload_today._notio, "update_workload_day", fake_update)
    monkeypatch.setattr(
        workload_today,
        "_steps_db",
        types.SimpleNamespace(upsert_step=fake_upsert),
    )

    result = (await router.dispatch(payload)).to_dict()

    with open(log, "a") as f:
        f.write("Step: dispatch\n")
        f.write(f"Output: {result}\n")

    dt = datetime.fromtimestamp(payload["timestamp"], timezone.utc)
    idx = dt.weekday()
    day_acc = [
        "понеділок",
        "вівторок",
        "середу",
        "четвер",
        "п'ятницю",
        "суботу",
        "неділю",
    ][idx]
    day_gen = [
        "понеділка",
        "вівторка",
        "середи",
        "четверга",
        "п'ятниці",
        "суботи",
        "неділі",
    ][idx]
    fact = int(
        resp["results"][0]["fact_0"]
        + resp["results"][0]["fact_1"]
        + resp["results"][0]["fact_2"]
    )
    capacity = int(resp["results"][0]["capacity"])
    hours = int(value)
    expected = (
        "Записав! \n"
        f"Заплановане навантаження у {day_acc}: {hours} год. \n"
        f"В щоденнику з понеділка до {day_gen}: {fact} год.\n"
        f"Капасіті на цей тиждень: {capacity} год."
    )
    assert result == {"output": expected}
