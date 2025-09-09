from typing import Any, Dict

from services.notion_connector import NotionConnector


_notio = NotionConnector()


async def handle(payload: Dict[str, Any]) -> str:
    """Handle the ``!register`` prefix command."""

    name = payload.get("result", {}).get("text", "").strip()
    user_id = payload.get("userId", "")
    channel_id = payload.get("channelId", "")

    try:
        result = await _notio.find_team_directory_by_channel(channel_id)
        results = result.get("results", [])
        page = results[0] if results else None
        if page and page.get("discord_id") and page.get("discord_id") != user_id:
            return "Канал вже зареєстрований на когось іншого."
        if not page:
            result = await _notio.find_team_directory_by_name(name)
            results = result.get("results", [])
            page = results[0] if results else None
        if page:
            if page.get("discord_id") and page.get("discord_id") != user_id:
                return "Канал вже зареєстрований на когось іншого."
            await _notio.update_team_directory_ids(page.get("id", ""), user_id, channel_id)
        else:
            await _notio.create_team_directory_page(name, user_id, channel_id)
        return f"Канал успішно зареєстровано на {name}"
    except Exception:
        return "Спробуй трохи піздніше. Я тут пораюсь по хаті."
