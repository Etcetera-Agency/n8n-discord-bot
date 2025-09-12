from typing import Any, Dict

from services.notion_connector import NotionConnector
from services.logging_utils import get_logger


_notio = NotionConnector()


async def handle(payload: Dict[str, Any]) -> str:
    """Handle the ``!register`` prefix command."""
    log = get_logger("register", payload)
    name = payload.get("result", {}).get("text", "").strip()
    user_id = payload.get("userId", "")
    channel_id = payload.get("channelId", "")

    try:
        log.debug("lookup channel", extra={"channel_id": channel_id})
        result = await _notio.find_team_directory_by_channel(channel_id)
        results = result.get("results", [])
        page = results[0] if results else None
        if page and page.get("discord_id") and page.get("discord_id") != user_id:
            log.info("channel taken", extra={"discord_id": page.get("discord_id")})
            return "Канал вже зареєстрований на когось іншого."
        if not page:
            log.debug("lookup name", extra={"member_name": name})
            result = await _notio.find_team_directory_by_name(name)
            results = result.get("results", [])
            page = results[0] if results else None
        if not page:
            return "Спробуй трохи піздніше. Я тут пораюсь по хаті."
        if page.get("discord_id") and page.get("discord_id") != user_id:
            log.info("channel taken", extra={"discord_id": page.get("discord_id")})
            return "Канал вже зареєстрований на когось іншого."
        await _notio.update_team_directory_ids(page.get("id", ""), user_id, channel_id)
        result_msg = f"Канал успішно зареєстровано на {name}"
        log.info("done register", extra={"page_id": page.get("id", ""), "output": result_msg})
        return result_msg
    except Exception:
        log.exception("failed register")
        return "Спробуй трохи піздніше. Я тут пораюсь по хаті."
