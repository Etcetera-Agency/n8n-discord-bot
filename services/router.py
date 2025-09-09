import logging
from typing import Any, Callable, Awaitable, Dict

from services.notion_connector import NotionConnector
from services.survey import survey_manager

logger = logging.getLogger(__name__)


async def handle_mention(payload: Dict[str, Any]) -> str:
    """Return placeholder response for mention queries."""
    user_id = payload.get("userId", "")
    return (
        "Я ще не вмію вільно розмовляти. "
        f"Використовуй слеш команди <@{user_id}>. Почни із /"
    )


HANDLERS: Dict[str, Callable[[Dict[str, Any]], Awaitable[str]]] = {
    "mention": handle_mention,
}

_notio = NotionConnector()


async def dispatch(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Route payloads to internal handlers."""
    todo_url = None
    try:
        result = await _notio.find_team_directory_by_channel(payload["channelId"])
        user = result.get("results", [{}])[0] if result.get("results") else {}
    except Exception as exc:  # pragma: no cover - defensive
        logger.error("Notion lookup failed: %s", exc)
        return {"output": str(exc)}

    if user:
        payload["userId"] = user.get("discord_id", payload.get("userId"))
        payload["author"] = user.get("name", payload.get("author"))
        todo_url = user.get("to_do")

        if payload.get("command") == "register":
            if user.get("is_public"):
                return {"output": "Публічні канали не можна реєструвати."}
            chan = str(user.get("channel_id", ""))
            if chan and len(chan) == 19:
                return {"output": "Канал вже зареєстрований на когось іншого."}

    user_id = payload.get("userId", "")
    active = any(s.user_id == user_id for s in survey_manager.surveys.values())
    if payload.get("command") == "survey" or active:
        step = payload.get("result", {}).get("stepName")
        handler = HANDLERS.get(step)
        if not handler:
            return {"output": f"No handler for step {step}", "survey": "cancel"}
        try:
            output = await handler(payload)
        except Exception as err:  # pragma: no cover - handler failure
            logger.error("Handler error: %s", err)
            return {"output": str(err), "survey": "cancel"}
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
        return response

    if payload.get("type") == "mention":
        output = await HANDLERS["mention"](payload)
        return {"output": output}

    command = payload.get("command")
    handler = HANDLERS.get(command)
    if not handler:
        return {"output": "Спробуй трохи піздніше. Я тут пораюсь по хаті."}
    try:
        output = await handler(payload)
    except Exception:  # pragma: no cover - handler failure
        return {"output": "Спробуй трохи піздніше. Я тут пораюсь по хаті."}
    return {"output": output}
