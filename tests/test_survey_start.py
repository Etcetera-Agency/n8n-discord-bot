import json
import re
import sys
import types
import importlib.util
import asyncio
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT))


def load_payload_example(title: str) -> dict:
    text = (ROOT / "payload_examples.txt").read_text()
    start = text.index(title)
    match = re.search(r"```json\n(.*?)\n```", text[start:], re.DOTALL)
    return json.loads(match.group(1))


def load_check_channel_response() -> dict:
    text = (ROOT / "responses").read_text()
    start = text.index("check_channel empty steps response")
    match = re.search(r"{\s*\"output\"[\s\S]*?}\s*}", text[start:])
    return json.loads(match.group(0))


def load_check_channel_nonmatching_response() -> dict:
    text = (ROOT / "responses").read_text()
    start = text.index("check_channel nonmatching steps response")
    match = re.search(r"{\s*\"output\"[\s\S]*?}\s*}", text[start:])
    return json.loads(match.group(0))


class DummyChannel:
    def __init__(self, cid: str):
        self.id = int(cid)
        self.messages = []

    async def send(self, msg):
        self.messages.append(msg)


def test_start_survey_without_steps(monkeypatch):
    # Stub config module
    class DummyLogger:
        def info(self, *a, **k):
            pass

        debug = warning = error = info

    config_stub = types.ModuleType("config")
    config_stub.ViewType = object
    config_stub.logger = DummyLogger()
    config_stub.Strings = types.SimpleNamespace(
        SURVEY_COMPLETE_MESSAGE="Всі данні внесені. Дякую!",
        SURVEY_START_ERROR="Сталася помилка",
    )
    config_stub.Config = types.SimpleNamespace()
    config_stub.constants = types.SimpleNamespace(SURVEY_FLOW=[])
    monkeypatch.setitem(sys.modules, "config", config_stub)

    # Stub services package and submodules
    services_stub = types.ModuleType("services")
    services_stub.__path__ = []
    created: dict = {}

    def create_survey(u, c, s, sess):
        survey = types.SimpleNamespace(
            user_id=u,
            channel_id=c,
            steps=s,
            session_id=sess,
            current_index=0,
            todo_url=None,
        )
        created["survey"] = survey
        return survey

    services_stub.survey_manager = types.SimpleNamespace(
        get_survey=lambda _cid: created.get("survey"),
        create_survey=create_survey,
        remove_survey=lambda _cid: None,
    )
    services_stub.webhook_service = types.SimpleNamespace(
        send_webhook_with_retry=None
    )
    services_stub.session_manager = types.SimpleNamespace()
    monkeypatch.setitem(sys.modules, "services", services_stub)
    notion_stub = types.ModuleType("services.notion_todos")
    notion_stub.Notion_todos = object
    monkeypatch.setitem(sys.modules, "services.notion_todos", notion_stub)
    survey_stub = types.ModuleType("services.survey")
    survey_stub.SurveyFlow = object
    monkeypatch.setitem(sys.modules, "services.survey", survey_stub)
    webhook_stub = types.ModuleType("services.webhook")
    webhook_stub.WebhookService = object
    monkeypatch.setitem(sys.modules, "services.webhook", webhook_stub)

    # Import survey module after stubbing
    spec = importlib.util.spec_from_file_location(
        "discord_bot.commands.survey", ROOT / "discord_bot" / "commands" / "survey.py"
    )
    survey_cmd = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(survey_cmd)
    Strings = config_stub.Strings

    payload = load_payload_example("check_channel Command Payload")
    channel_id = "123"
    user_id = "321"
    session_id = f"{channel_id}_{user_id}"
    expected = dict(payload)
    expected["channelId"] = channel_id
    expected["sessionId"] = session_id

    response = load_check_channel_response()
    called = {"payloads": []}

    async def fake_send_webhook(target, payload_arg, headers):
        called["payloads"].append(payload_arg)
        # Simulate router populating todo_url on second call
        if len(called["payloads"]) == 2 and created.get("survey"):
            created["survey"].todo_url = "https://todo.url"
        return True, response

    monkeypatch.setattr(
        survey_cmd.webhook_service, "send_webhook_with_retry", fake_send_webhook
    )
    channel = DummyChannel(channel_id)

    async def fake_fetch_channel(cid):
        assert str(cid) == channel_id
        return channel

    bot = types.SimpleNamespace(fetch_channel=fake_fetch_channel)

    async def fake_finish(bot_arg, channel_arg, survey_arg):
        await channel_arg.send(Strings.SURVEY_COMPLETE_MESSAGE)

    monkeypatch.setattr(survey_cmd, "finish_survey", fake_finish)

    asyncio.run(
        survey_cmd.handle_start_daily_survey(bot, user_id, channel_id, session_id)
    )

    assert called["payloads"] == [expected, expected]
    assert channel.messages == [Strings.SURVEY_COMPLETE_MESSAGE]
    assert created["survey"].todo_url == "https://todo.url"


def test_start_survey_no_required_steps(monkeypatch):
    class DummyLogger:
        def info(self, *a, **k):
            pass

        debug = warning = error = info

    config_stub = types.ModuleType("config")
    config_stub.ViewType = object
    config_stub.logger = DummyLogger()
    config_stub.Strings = types.SimpleNamespace(
        SURVEY_COMPLETE_MESSAGE="Всі данні внесені. Дякую!",
        SURVEY_START_ERROR="Сталася помилка",
    )
    config_stub.Config = types.SimpleNamespace()
    # SURVEY_FLOW excludes returned steps
    config_stub.constants = types.SimpleNamespace(SURVEY_FLOW=["workload_today"])
    monkeypatch.setitem(sys.modules, "config", config_stub)

    services_stub = types.ModuleType("services")
    services_stub.__path__ = []
    created = {}

    def create_survey(u, c, s, sess):
        survey = types.SimpleNamespace(
            user_id=u,
            channel_id=c,
            steps=s,
            session_id=sess,
            current_index=0,
            todo_url=None,
        )
        created["survey"] = survey
        created["steps"] = s
        return survey

    services_stub.survey_manager = types.SimpleNamespace(
        get_survey=lambda _cid: created.get("survey"),
        create_survey=create_survey,
        remove_survey=lambda _cid: None,
    )
    services_stub.webhook_service = types.SimpleNamespace(send_webhook_with_retry=None)
    services_stub.session_manager = types.SimpleNamespace()
    monkeypatch.setitem(sys.modules, "services", services_stub)
    notion_stub = types.ModuleType("services.notion_todos")
    notion_stub.Notion_todos = object
    monkeypatch.setitem(sys.modules, "services.notion_todos", notion_stub)
    survey_stub = types.ModuleType("services.survey")
    survey_stub.SurveyFlow = object
    monkeypatch.setitem(sys.modules, "services.survey", survey_stub)
    webhook_stub = types.ModuleType("services.webhook")
    webhook_stub.WebhookService = object
    monkeypatch.setitem(sys.modules, "services.webhook", webhook_stub)

    spec = importlib.util.spec_from_file_location(
        "discord_bot.commands.survey", ROOT / "discord_bot" / "commands" / "survey.py"
    )
    survey_cmd = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(survey_cmd)
    Strings = config_stub.Strings

    payload = load_payload_example("check_channel Command Payload")
    channel_id = "123"
    user_id = "321"
    session_id = f"{channel_id}_{user_id}"
    expected = dict(payload)
    expected["channelId"] = channel_id
    expected["sessionId"] = session_id

    response = load_check_channel_nonmatching_response()
    called = {"payloads": []}

    async def fake_send_webhook(target, payload_arg, headers):
        called["payloads"].append(payload_arg)
        if len(called["payloads"]) == 2 and created.get("survey"):
            created["survey"].todo_url = "https://todo.url"
        return True, response

    monkeypatch.setattr(
        survey_cmd.webhook_service, "send_webhook_with_retry", fake_send_webhook
    )
    channel = DummyChannel(channel_id)

    async def fake_fetch_channel(cid):
        assert str(cid) == channel_id
        return channel

    bot = types.SimpleNamespace(fetch_channel=fake_fetch_channel)

    async def fake_finish(bot_arg, channel_arg, survey_arg):
        await channel_arg.send(Strings.SURVEY_COMPLETE_MESSAGE)

    monkeypatch.setattr(survey_cmd, "finish_survey", fake_finish)

    asyncio.run(
        survey_cmd.handle_start_daily_survey(bot, user_id, channel_id, session_id)
    )

    assert called["payloads"] == [expected, expected]
    assert channel.messages == [Strings.SURVEY_COMPLETE_MESSAGE]
    assert created["steps"] == []
    assert created["survey"].todo_url == "https://todo.url"
