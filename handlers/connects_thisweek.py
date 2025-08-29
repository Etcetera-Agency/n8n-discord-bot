"""Handler for the 'connects_thisweek' command."""
from datetime import datetime
import dto
from services import survey
from clients.http import HttpClient
from clients.notion import NotionClient
from clients.postgres import PostgresClient

# In a real application, this URL would come from a configuration file.
HTTP_CONNECTS_URL = "https://example.com/api/connects"

# Response Templates
USER_NOT_FOUND_TEMPLATE = "Your Discord ID is not found in our Notion database. Please contact an administrator."
INVALID_INPUT_TEMPLATE = "Please provide a valid number of connects (e.g., 5, 0)."
SUCCESS_TEMPLATE = "Your connects for this week have been recorded as {count}."
FOOTER_TEMPLATE = "#{channel}  •  {time}"

def handle_connects_thisweek(request: dto.CommandRequest) -> dto.CommandResponse:
    """
    Handles the 'connects_thisweek' command by sending an HTTP request,
    updating Notion non-fatally, and marking the step as complete.
    """
    try:
        if request.result is None or request.result.text is None:
            raise ValueError("Missing input")
        count = int(request.result.text)
        if count < 0:
            raise ValueError("Negative count is not allowed.")
    except (ValueError, TypeError):
        return dto.CommandResponse(output=INVALID_INPUT_TEMPLATE)

    # Placeholder instantiations for clients
    http_client, notion_client, pg_client = HttpClient(), NotionClient(), PostgresClient()

    user_page = notion_client.find_user_by_discord_id(discord_id=request.userId)
    if not user_page or 'id' not in user_page:
        return dto.CommandResponse(output=USER_NOT_FOUND_TEMPLATE)

    # Send data to an external HTTP endpoint
    http_payload = {"userId": request.userId, "connects": count, "channelId": request.channelId}
    http_client.post(url=HTTP_CONNECTS_URL, json_data=http_payload)

    # Update Notion, but do not fail the entire operation if this step fails.
    try:
        notion_client.update_user_connects(notion_page_id=user_page['id'], connects_count=count)
    except Exception as e:
        # In a real application, this error would be logged to a monitoring service.
        print(f"NON-FATAL ERROR: Failed to update Notion for user {request.userId}. Reason: {e}")
        pass

    # Mark the survey step as complete in the database
    pg_client.upsert_survey_step(session_id=request.channelId, step_name="connects_thisweek", completed=True)

    # Format the success response
    now_kyiv = datetime.now(survey.TZ_KYIV)
    time_str = now_kyiv.strftime("%H:%M")
    body = SUCCESS_TEMPLATE.format(count=count)
    footer = FOOTER_TEMPLATE.format(channel=request.channelId, time=time_str)

    return dto.CommandResponse(output=f"{body}\n{footer}")
