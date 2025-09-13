from typing import Any, Callable, Awaitable, Dict, Optional, Union

from services.notion_connector import NotionConnector
from config import Strings
from services.survey import survey_manager
from services.survey_models import SurveyStep, SurveyResult, SurveyEvent
from services.payload_models import BotRequestPayload, RouterResponse
from services.cmd import (
    register,
    unregister,
    workload_today,
    workload_nextweek,
    connects_thisweek,
    day_off,
    vacation,
    check_channel,
)
from services.logging_utils import get_logger, wrap_handler, wrap_survey_handler, current_context


async def handle_mention(payload: Dict[str, Any]) -> str:
    """Return placeholder response for mention queries."""
    user_id = payload.get("userId", "")
    return (
        "Я ще не вмію вільно розмовляти. "
        f"Використовуй слеш команди <@{user_id}>. Почни із /"
    )


SURVEY_STEP_NAMES = {
    "workload_today",
    "workload_nextweek",
    "connects_thisweek",
    "day_off",
    "day_off_thisweek",
    "day_off_nextweek",
    "vacation",
}

HANDLERS: Dict[str, Callable[[Any], Awaitable[str]]] = {
    "mention": wrap_handler("mention", handle_mention),
    "register": wrap_handler("register", register.handle),
    "unregister": wrap_handler("unregister", unregister.handle),
    # Survey-related handlers receive typed SurveyEvent
    "workload_today": wrap_survey_handler("workload_today", workload_today.handle),
    "workload_nextweek": wrap_survey_handler("workload_nextweek", workload_nextweek.handle),
    "connects_thisweek": wrap_survey_handler("connects_thisweek", connects_thisweek.handle),
    "day_off": wrap_survey_handler("day_off", day_off.handle),
    "day_off_thisweek": wrap_survey_handler("day_off_thisweek", day_off.handle),
    "day_off_nextweek": wrap_survey_handler("day_off_nextweek", day_off.handle),
    "vacation": wrap_survey_handler("vacation", vacation.handle),
    # Non-survey
    "check_channel": wrap_handler("check_channel", check_channel.handle),
}

_notio = NotionConnector()


def parse_prefix(message: str) -> Optional[Dict[str, Any]]:
    """Parse `!` prefix commands from a message string."""
    if not message:
        return None
    if message.startswith("!register"):
        name = message[len("!register") :].strip()
        return {"command": "register", "result": {"text": name}}
    if message.startswith("!unregister"):
        return {"command": "unregister", "result": {}}
    return None


async def dispatch(payload: Union[Dict[str, Any], BotRequestPayload]) -> RouterResponse:
    """Route payloads to internal handlers with contextual logging.

    Accepts either a raw dict or a validated BotRequestPayload model
    and returns a typed RouterResponse.
    """
    # Normalize incoming payload to a model and a working dict copy
    try:
        model = payload if isinstance(payload, BotRequestPayload) else BotRequestPayload.from_dict(payload)
        payload_dict: Dict[str, Any] = payload.to_dict() if isinstance(payload, BotRequestPayload) else dict(payload)
    except Exception:
        log = get_logger("router.dispatch")
        log.exception("failed to validate payload")
        return RouterResponse(output=Strings.TRY_AGAIN_LATER)

    ctx = {
        "session_id": model.sessionId,
        "user": model.userId,
        "channel": model.channelId,
        "step_name": "router.dispatch",
    }
    token = current_context.set(ctx)
    log = get_logger("router.dispatch", payload_dict)
    log.info("start")
    log.debug("payload", extra={"payload": payload_dict})

    def finalize(resp: RouterResponse) -> RouterResponse:
        out = resp.to_dict()
        log.debug("response ready", extra={"output": out})
        log.info("done")
        current_context.reset(token)
        return resp

    try:
        prefix = parse_prefix(payload_dict.get("message", ""))
        if prefix:
            payload_dict.update(prefix)

        todo_url = None
        channel = model.channelId
        log.debug(f"query team directory for channel {channel}", extra={"channel": channel})
        result = await _notio.find_team_directory_by_channel(model.channelId)
        user = result.get("results", [{}])[0] if result.get("results") else {}
        log.debug("notion response", extra={"user": user})
        if not user:
            return finalize(RouterResponse(output="Користувач не знайдений"))

        payload_dict["userId"] = user.get("discord_id", payload_dict.get("userId"))
        payload_dict["author"] = user.get("name", payload_dict.get("author"))
        # keep model in sync with enriched fields
        try:
            model.userId = payload_dict["userId"]
            model.author = payload_dict["author"]
        except Exception:
            pass
        todo_url = user.get("to_do")

        survey_state = survey_manager.get_survey(channel)
        if survey_state and todo_url:
            survey_state.todo_url = todo_url

        if payload_dict.get("command") == "register":
            if user.get("is_public"):
                return finalize(RouterResponse(output="Публічні канали не можна реєструвати."))
            chan = str(user.get("channel_id", ""))
            if chan and len(chan) == 19:
                return finalize(RouterResponse(output="Канал вже зареєстрований на когось іншого."))

        command = payload_dict.get("command")

        def build_survey_event(step_name: str) -> SurveyEvent:
            # Extract and normalize value according to step
            res = dict(payload_dict.get("result") or {})
            value: Any
            if step_name == "connects_thisweek":
                value = res.get("connects", res.get("value"))
            elif step_name in ("day_off_thisweek", "day_off_nextweek", "day_off"):
                value = res.get("value", res.get("daysSelected"))
            elif step_name == "vacation":
                # pass through the entire result dict with start/end keys
                value = res
            else:
                value = res.get("value") if "value" in res else res.get("workload")

            step_obj = SurveyStep(name=step_name)
            result_obj = SurveyResult(step_name=step_name, value=value)
            return SurveyEvent(step=step_obj, result=result_obj, payload=model)

        # Treat survey as active if there's a channel-scoped survey state
        channel_active = survey_state is not None
        if command == "survey" or (channel_active and command not in HANDLERS):
            step = payload_dict.get("result", {}).get("stepName")
            handler = HANDLERS.get(step)
            if not handler:
                return finalize(RouterResponse(output=f"No handler for step {step}", survey="cancel"))

            event = build_survey_event(step)
            try:
                output = await handler(event)
            except Exception as err:  # pragma: no cover - handler failure
                log.exception("handler error")
                return finalize(RouterResponse(output=str(err), survey="cancel"))

            # Record result via SurveyManager without advancing state.
            # Flow control (continue/end) is determined in Discord layer via survey_manager state.
            if survey_state:
                survey_manager.record_step_result(
                    payload_dict.get("channelId"), step, event.result.value
                )
            return finalize(RouterResponse(output=output))

        if payload_dict.get("type") == "mention":
            output = await HANDLERS["mention"](payload_dict)
            return finalize(RouterResponse(output=output))

        handler = HANDLERS.get(command)
        if not handler:
            return finalize(RouterResponse(output=Strings.TRY_AGAIN_LATER))
        try:
            if command in SURVEY_STEP_NAMES:
                event = build_survey_event(command)
                output = await handler(event)
            else:
                output = await handler(payload_dict)
        except Exception:  # pragma: no cover - handler failure
            log.exception("handler error")
            return finalize(RouterResponse(output=Strings.TRY_AGAIN_LATER))
        return finalize(RouterResponse(output=output))
    except Exception:  # pragma: no cover - defensive
        log.exception("failed")
        return finalize(RouterResponse(output=Strings.TRY_AGAIN_LATER))
