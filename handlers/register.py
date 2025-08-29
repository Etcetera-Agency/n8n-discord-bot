"""Handler for the 'register' command."""
import re
import dto
from clients.notion import NotionClient

# In a real application, this list would be managed via configuration.
PUBLIC_CHANNELS = ["1088421536295440434", "1088421575825231922"]

# Response templates should be managed in a dedicated module,
# but are included here for simplicity in this step.
# Note the trailing spaces, which are preserved as per requirements.
REGISTER_SUCCESS_TEMPLATE = "You are now registered to receive survey notifications in this channel. "
USER_NOT_FOUND_TEMPLATE = "Your Discord ID is not found in our Notion database. Please contact an administrator."
INVALID_CHANNEL_TEMPLATE = "Registration is only allowed in public team channels."
INVALID_CHANNEL_ID_TEMPLATE = "Invalid channel ID format. It must be a 19-digit number."

def handle_register(request: dto.CommandRequest) -> dto.CommandResponse:
    """
    Handles user registration by validating the channel and updating
    the user's profile in Notion with the channel ID.
    """
    channel_id = request.channelId
    user_id = request.userId

    # 1. Validate channel ID format (must be a 19-digit string)
    if not re.fullmatch(r"\d{19}", channel_id):
        return dto.CommandResponse(output=INVALID_CHANNEL_ID_TEMPLATE)

    # 2. Validate against public channel list
    if channel_id not in PUBLIC_CHANNELS:
        return dto.CommandResponse(output=INVALID_CHANNEL_TEMPLATE)

    # 3. Find user in Notion and update their record
    # Placeholder instantiation; this would be injected in a real app.
    notion_client = NotionClient()
    user_page = notion_client.find_user_by_discord_id(discord_id=user_id)

    if not user_page or 'id' not in user_page:
        return dto.CommandResponse(output=USER_NOT_FOUND_TEMPLATE)

    notion_page_id = user_page['id']
    notion_client.update_user_channel(notion_page_id=notion_page_id, channel_id=channel_id)

    # 4. Return success response
    return dto.CommandResponse(output=REGISTER_SUCCESS_TEMPLATE)
