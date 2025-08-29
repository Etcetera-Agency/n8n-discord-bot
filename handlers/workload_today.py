"""Handler for the 'workload_today' command."""
from datetime import datetime
import dto
from services import survey
from clients.notion import NotionClient
from clients.postgres import PostgresClient

# Response Templates
USER_NOT_FOUND_TEMPLATE = "Your Discord ID is not found in our Notion database. Please contact an administrator."
INVALID_INPUT_TEMPLATE = "Please provide a valid number of hours (e.g., 8, 4, 0)."
SUCCESS_TEMPLATE = "Your workload for today has been updated to {hours} hours.\nThank you!"
FOOTER_TEMPLATE = "#{channel}  •  {time}"

def handle_workload_today(request: dto.CommandRequest) -> dto.CommandResponse:
    """
    Handles the 'workload_today' command by parsing user input,
    updating Notion, and marking the survey step as complete.
    """
    try:
        if request.result is None or request.result.text is None:
            raise ValueError("Missing input")
        hours = int(request.result.text)
        if hours < 0:
            raise ValueError("Negative hours are not allowed.")
    except (ValueError, TypeError):
        return dto.CommandResponse(output=INVALID_INPUT_TEMPLATE)

    # Placeholder instantiations for clients
    notion_client = NotionClient()
    pg_client = PostgresClient()

    user_page = notion_client.find_user_by_discord_id(discord_id=request.userId)
    if not user_page or 'id' not in user_page:
        return dto.CommandResponse(output=USER_NOT_FOUND_TEMPLATE)

    # Update Notion with the workload
    notion_client.update_user_workload(
        notion_page_id=user_page['id'],
        field_name="Workload today",
        hours=hours
    )

    # Mark the step as complete in the database
    pg_client.upsert_survey_step(
        session_id=request.channelId,
        step_name="workload_today",
        completed=True
    )

    # Format the success response with the required footer
    now_kyiv = datetime.now(survey.TZ_KYIV)
    time_str = now_kyiv.strftime("%H:%M")

    body = SUCCESS_TEMPLATE.format(hours=hours)
    footer = FOOTER_TEMPLATE.format(channel=request.channelId, time=time_str)

    return dto.CommandResponse(output=f"{body}\n{footer}")
