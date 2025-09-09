from typing import Any, Dict

from services.notion_connector import NotionConnector

_notio = NotionConnector()


async def handle(payload: Dict[str, Any]) -> str:
    channel_id = payload.get("channelId", "")
    try:
        data = await _notio.find_team_directory_by_channel(channel_id)
        page = data.get("results", [])
        if not page:
            return (
                "Вибачте, але цей канал не зареєстрований ні на кого. Тому не можу зняти його з реєстрації"
            )
        page_id = page[0]["id"]
        await _notio.clear_team_directory_ids(page_id)
        return "Готово. Тепер цей канал не зареєстрований ні на кого."
    except Exception:
        return "Спробуй трохи піздніше. Я тут пораюсь по хаті."
