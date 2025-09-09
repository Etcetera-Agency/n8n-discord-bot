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
from services.survey_steps_db import SurveyStepsDB

SCENARIO_DIR = Path(__file__).parent / "surveys"
LOG_DIR = Path(__file__).parent / "logs"

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend():
    return "asyncio"


def load_payload_example(title: str) -> dict:
    text = (ROOT / "payload_examples.txt").read_text()
    start = text.index(title)
    block = text[start:]
    json_start = block.index("```json\n") + len("```json\n")
    after = block[json_start:]
    end_backticks = after.find("```")
    end_heading = after.find("\n##")
    candidates = [i for i in (end_backticks, end_heading) if i != -1]
    end = min(candidates) if candidates else len(after)
    json_text = after[:end]
    return json.loads(json_text)


def load_notion_lookup(responses_path: Path) -> dict:
    text = responses_path.read_text()
    try:
        data = json.loads(text)
        td = data["team_directory"][0]
        name = td["property_name"]
        todo_url = td["property_to_do"].strip()
    except Exception:
        name = re.search(r'plain_text": "([^"]+Lernichenko)"', text).group(1)
        todo_url = re.search(r'https://www.notion.so/[0-9a-f-]+', text).group(0)
    return {"results": [{"name": name, "discord_id": "321", "channel_id": "123", "to_do": todo_url}]}


def scenarios():
    return [p for p in SCENARIO_DIR.iterdir() if p.is_dir()]


@pytest.mark.parametrize("scenario_path", scenarios())
async def test_survey_scenario(monkeypatch, scenario_path):
    with open(scenario_path / "dbSetup.json") as f:
        json.load(f)  # placeholder for future DB setup
    notion_cfg = json.load(open(scenario_path / "notionResponses.json"))
    responses_path = ROOT / notion_cfg["file"]
    lookup_data = load_notion_lookup(responses_path)

    log = logging.getLogger("test")

    async def lookup(channel_id):
        log.debug("notion lookup", extra={"channel": channel_id})
        log.debug("notion lookup response", extra={"result": lookup_data})
        return lookup_data

    monkeypatch.setattr(router._notio, "find_team_directory_by_channel", lookup)

    steps = json.load(open(scenario_path / "steps.json"))
    handler_outputs = {s["stepName"]: s["bot"] for s in steps}
    for name, output in handler_outputs.items():
        async def fake_handler(payload, _out=output):
            return _out
        monkeypatch.setitem(router.HANDLERS, name, fake_handler)

    step_order = [s["stepName"] for s in steps]

    async def fake_fetch_week(self, channel_id, start):
        return [
            {"step_name": name, "completed": False, "updated": ""}
            for name in step_order
        ]
    monkeypatch.setattr(SurveyStepsDB, "fetch_week", fake_fetch_week)

    router.survey_manager.surveys.clear()

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_file = LOG_DIR / f"{scenario_path.name}.log"

    class JsonFormatter(logging.Formatter):
        def format(self, record):
            data = {
                "time": self.formatTime(record, self.datefmt),
                "level": record.levelname,
                "message": record.getMessage(),
            }
            for k, v in record.__dict__.items():
                if k not in (
                    "name",
                    "msg",
                    "args",
                    "levelname",
                    "levelno",
                    "pathname",
                    "filename",
                    "module",
                    "exc_info",
                    "exc_text",
                    "stack_info",
                    "lineno",
                    "funcName",
                    "created",
                    "msecs",
                    "relativeCreated",
                    "thread",
                    "threadName",
                    "processName",
                    "process",
                ):
                    data[k] = v
            return json.dumps(data, ensure_ascii=False)

    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(JsonFormatter())
    log.setLevel(logging.DEBUG)
    log.addHandler(file_handler)

    try:
        check = load_payload_example("check_channel Command Payload")
        check["userId"] = "321"
        check["channelId"] = "123"
        check["sessionId"] = "123_321"
        log.info("step start", extra={"step": "check_channel"})
        log.debug("dispatch payload", extra={"payload": check})
        start_resp = await router.dispatch(check)
        log.debug("dispatch response", extra={"response": start_resp})
        log.info("step done", extra={"step": "check_channel"})
        start_steps = start_resp["output"]["steps"]
        router.survey_manager.create_survey("321", "123", start_steps, "123_321")

        for step in steps:
            payload = load_payload_example(step["title"])
            payload["userId"] = "321"
            payload["channelId"] = "123"
            payload["sessionId"] = "123_321"
            payload["result"]["stepName"] = step["stepName"]
            if "payloadOverride" in step:
                payload["result"].update(step["payloadOverride"])

            log.info("step start", extra={"step": step["stepName"]})
            log.debug("dispatch payload", extra={"payload": payload})
            response = await router.dispatch(payload)
            active = router.survey_manager.get_survey("123") is not None
            log.debug(
                "dispatch response", extra={"response": response, "survey_active": active}
            )
            log.info("step done", extra={"step": step["stepName"]})

            expected = {"output": step["bot"], **step["expected"]}
            if "$TODO_URL" in json.dumps(expected):
                todo_url = lookup_data["results"][0]["to_do"]
                expected = json.loads(
                    json.dumps(expected).replace("$TODO_URL", todo_url)
                )
            assert response == expected
            active_expected = step["dbExpected"]["active"]
            if active_expected:
                assert active
            else:
                assert not active
    finally:
        log.removeHandler(file_handler)
        file_handler.close()
