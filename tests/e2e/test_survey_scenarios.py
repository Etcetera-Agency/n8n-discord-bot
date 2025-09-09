import sys
import json
import re
from pathlib import Path
import pytest
import types
import logging

ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(ROOT))
sys.path.append(str(ROOT / "services"))

class DummyConfig:
    DATABASE_URL = ""
    NOTION_TEAM_DIRECTORY_DB_ID = ""
    NOTION_TOKEN = ""
    NOTION_WORKLOAD_DB_ID = ""
    NOTION_PROFILE_STATS_DB_ID = ""
    WEBHOOK_AUTH_TOKEN = ""
    SESSION_TTL = 1

sys.modules["config"] = types.SimpleNamespace(
    Config=DummyConfig, logger=logging.getLogger("test"), Strings=object()
)

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

databases_mod = types.ModuleType("databases")
class DummyDatabase:
    def __init__(self, *args, **kwargs):
        self.is_connected = False
    async def connect(self):
        self.is_connected = True
    async def disconnect(self):
        self.is_connected = False
    async def execute(self, *args, **kwargs):
        pass
    async def fetch_all(self, *args, **kwargs):
        return []
databases_mod.Database = DummyDatabase
sys.modules["databases"] = databases_mod

import router

SCENARIO_DIR = Path(__file__).parent / "surveys"
LOG_DIR = Path(__file__).parent / "logs"


def load_payload_example(title: str) -> dict:
    text = (ROOT / "payload_examples.txt").read_text()
    start = text.index(title)
    match = re.search(r"```json\n(.*?)\n```", text[start:], re.DOTALL)
    return json.loads(match.group(1))


def load_notion_lookup(responses_path: Path) -> dict:
    text = responses_path.read_text()
    name = re.search(r'plain_text": "([^"]+Lernichenko)"', text).group(1)
    todo_url = re.search(r'https://www.notion.so/[0-9a-f-]+', text).group(0)
    return {"results": [{"name": name, "discord_id": "321", "channel_id": "123", "to_do": todo_url}]}


def scenarios():
    return [p for p in SCENARIO_DIR.iterdir() if p.is_dir()]


@pytest.mark.asyncio
@pytest.mark.parametrize("scenario_path", scenarios())
async def test_survey_scenario(monkeypatch, scenario_path):
    with open(scenario_path / "dbSetup.json") as f:
        json.load(f)  # placeholder for future DB setup
    notion_cfg = json.load(open(scenario_path / "notionResponses.json"))
    responses_path = ROOT / notion_cfg["file"]
    lookup_data = load_notion_lookup(responses_path)

    async def lookup(channel_id):
        return lookup_data

    monkeypatch.setattr(router._notio, "find_team_directory_by_channel", lookup)

    steps = json.load(open(scenario_path / "steps.json"))
    handler_outputs = {s["stepName"]: s["bot"] for s in steps}
    for name, output in handler_outputs.items():
        async def handler(payload, _out=output):
            return _out
        monkeypatch.setitem(router.HANDLERS, name, handler)

    step_order = [s["stepName"] for s in steps]
    router.survey_manager.surveys.clear()
    router.survey_manager.create_survey("321", "123", step_order, "sess")

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_file = LOG_DIR / f"{scenario_path.name}.log"
    with log_file.open("w") as log:
        for step in steps:
            payload = load_payload_example(step["title"])
            payload["userId"] = "321"
            payload["channelId"] = "123"
            payload["sessionId"] = "123_321"
            payload["result"]["stepName"] = step["stepName"]
            response = await router.dispatch(payload)
            log.write(json.dumps({"payload": payload, "response": response}) + "\n")
            expected = {"output": step["bot"], **step["expected"]}
            if "$TODO_URL" in json.dumps(expected):
                todo_url = lookup_data["results"][0]["to_do"]
                expected = json.loads(json.dumps(expected).replace("$TODO_URL", todo_url))
            assert response == expected
            active = step["dbExpected"]["active"]
            if active:
                assert router.survey_manager.get_survey("123") is not None
            else:
                assert router.survey_manager.get_survey("123") is None
