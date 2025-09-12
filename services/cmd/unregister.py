from typing import Any, Dict

from services.notion_connector import NotionConnector
from services.logging_utils import get_logger

_notio = NotionConnector()


async def handle(payload: Dict[str, Any]) -> str:
    log = get_logger("unregister", payload)
    channel_id = payload.get("channelId", "")
    try:
        log.debug("lookup channel", extra={"channel_id": channel_id})
        data = await _notio.find_team_directory_by_channel(channel_id)
        page = data.get("results", [])
        if not page:
            log.info("channel not registered")
            return (
                "Вибачте, але цей канал не зареєстрований ні на кого. Тому не можу зняти його з реєстрації"
            )
        page_id = page[0]["id"]
        await _notio.clear_team_directory_ids(page_id)
        result = "Готово. Тепер цей канал не зареєстрований ні на кого."
        log.info("done unregister", extra={"page_id": page_id, "output": result})
        return result
    except Exception:
        log.exception("failed unregister")
        return "Спробуй трохи піздніше. Я тут пораюсь по хаті."
