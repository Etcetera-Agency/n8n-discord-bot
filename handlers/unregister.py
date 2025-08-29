"""Handler for the 'unregister' command."""
import dto
from clients.notion import NotionClient

# Response templates
UNREGISTER_SUCCESS_TEMPLATE = "You have been unregistered and will no longer receive survey notifications. "
USER_NOT_FOUND_TEMPLATE = "Your Discord ID is not found in our Notion database. Please contact an administrator."

def handle_unregister(request: dto.CommandRequest) -> dto.CommandResponse:
    """Handles user de-registration."""
    user_id = request.userId

    notion_client = NotionClient() # Placeholder instantiation
    user_page = notion_client.find_user_by_discord_id(discord_id=user_id)

    if not user_page or 'id' not in user_page:
        return dto.CommandResponse(output=USER_NOT_FOUND_TEMPLATE)

    notion_page_id = user_page['id']
    notion_client.clear_user_channel(notion_page_id=notion_page_id)

    return dto.CommandResponse(output=UNREGISTER_SUCCESS_TEMPLATE)
