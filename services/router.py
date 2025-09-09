from typing import Any, Callable, Awaitable, Dict, Optional

from services.notion_connector import NotionConnector
from services.survey import survey_manager
from services.cmd import (
    register,
    unregister,
    workload_today,
    workload_nextweek,
    connects_this_week,
    day_off,
    vacation,
    check_channel,
)
from services.logging_utils import get_logger, wrap_handler, current_context


async def handle_mention(payload: Dict[str, Any]) -> str:
    """Return placeholder response for mention queries."""
    user_id = payload.get("userId", "")
    return (
        "Я ще не вмію вільно розмовляти. "
        f"Використовуй слеш команди <@{user_id}>. Почни із /"
    )


HANDLERS: Dict[str, Callable[[Dict[str, Any]], Awaitable[str]]] = {
    "mention": wrap_handler("mention", handle_mention),
    "register": wrap_handler("register", register.handle),
    "unregister": wrap_handler("unregister", unregister.handle),
    "workload_today": wrap_handler("workload_today", workload_today.handle),
    "workload_nextweek": wrap_handler("workload_nextweek", workload_nextweek.handle),
    "connects_this_week": wrap_handler("connects_this_week", connects_this_week.handle),
    "day_off": wrap_handler("day_off", day_off.handle),
    "day_off_thisweek": wrap_handler("day_off_thisweek", day_off.handle),
    "day_off_nextweek": wrap_handler("day_off_nextweek", day_off.handle),
    "vacation": wrap_handler("vacation", vacation.handle),
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


async def dispatch(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Route payloads to internal handlers with contextual logging."""
    ctx = {
        "session_id": payload.get("sessionId"),
        "user": payload.get("userId"),
        "channel": payload.get("channelId"),
        "step_name": "router.dispatch",
    }
    token = current_context.set(ctx)
    log = get_logger("router.dispatch", payload)
    log.info("start")
    log.debug("payload", extra={"payload": payload})

    def finalize(resp: Dict[str, Any]) -> Dict[str, Any]:
        log.debug("response ready", extra={"output": resp})
        log.info("done")
        current_context.reset(token)
        return resp

    try:
        prefix = parse_prefix(payload.get("message", ""))
        if prefix:
            payload.update(prefix)

        todo_url = None
        log.debug("query team directory", extra={"channel": payload.get("channelId")})
        result = await _notio.find_team_directory_by_channel(payload["channelId"])
        user = result.get("results", [{}])[0] if result.get("results") else {}
        log.debug("notion response", extra={"user": user})
        if not user:
            return finalize({"output": "Користувач не знайдений"})

        payload["userId"] = user.get("discord_id", payload.get("userId"))
        payload["author"] = user.get("name", payload.get("author"))
        todo_url = user.get("to_do")

        if payload.get("command") == "register":
            if user.get("is_public"):
                return finalize({"output": "Публічні канали не можна реєструвати."})
            chan = str(user.get("channel_id", ""))
            if chan and len(chan) == 19:
                return finalize({"output": "Канал вже зареєстрований на когось іншого."})

        user_id = payload.get("userId", "")
        command = payload.get("command")
        active = any(s.user_id == user_id for s in survey_manager.surveys.values())
        if command == "survey" or (active and command not in HANDLERS):
            step = payload.get("result", {}).get("stepName")
            handler = HANDLERS.get(step)
            if not handler:
                return finalize({"output": f"No handler for step {step}", "survey": "cancel"})
            try:
                output = await handler(payload)
            except Exception as err:  # pragma: no cover - handler failure
                log.exception("handler error")
                return finalize({"output": str(err), "survey": "cancel"})
            survey = survey_manager.get_survey(payload.get("channelId"))
            flag = "cancel"
            next_step = None
            if survey:
                survey.add_result(step, payload.get("result", {}).get("value"))
                survey.next_step()
                next_step = survey.current_step()
                if survey.is_done():
                    flag = "end"
                    survey_manager.remove_survey(payload.get("channelId"))
                else:
                    flag = "continue"
            response = {"output": output, "survey": flag}
            if next_step:
                response["next_step"] = next_step
            if flag == "end" and todo_url:
                response["url"] = todo_url
            return finalize(response)

        if payload.get("type") == "mention":
            output = await HANDLERS["mention"](payload)
            return finalize({"output": output})

        handler = HANDLERS.get(command)
        if not handler:
            return finalize({"output": "Спробуй трохи піздніше. Я тут пораюсь по хаті."})
        try:
            output = await handler(payload)
        except Exception:  # pragma: no cover - handler failure
            log.exception("handler error")
            return finalize({"output": "Спробуй трохи піздніше. Я тут пораюсь по хаті."})
        return finalize({"output": output})
    except Exception:  # pragma: no cover - defensive
        log.exception("failed")
        return finalize({"output": "Спробуй трохи піздніше. Я тут пораюсь по хаті."})
