"""Handler for the 'vacation' command."""
from datetime import datetime
import dto
from services import survey
from clients.notion import NotionClient
from clients.gcal import GCalClient

# Response Templates
USER_NOT_FOUND_TEMPLATE = "Your Discord ID is not found in our Notion database. Please contact an administrator to get your email set up."
INVALID_DATE_FORMAT_TEMPLATE = "Please use the format YYYY-MM-DD to YYYY-MM-DD for the date range."
SUCCESS_TEMPLATE = "Your vacation from {start_date} to {end_date} has been scheduled. Have a great time!"
FOOTER_TEMPLATE = "#{channel}  •  {time}"

def handle_vacation(request: dto.CommandRequest) -> dto.CommandResponse:
    """
    Handles scheduling a vacation by creating a multi-day event in Google Calendar.
    """
    try:
        if request.result is None or request.result.text is None:
            raise ValueError("Missing input")
        parts = request.result.text.split(' to ')
        if len(parts) != 2: raise ValueError("Invalid range format")
        start_date = datetime.strptime(parts[0], "%Y-%m-%d").date()
        end_date = datetime.strptime(parts[1], "%Y-%m-%d").date()
        if start_date > end_date: raise ValueError("Start date is after end date")
    except ValueError:
        return dto.CommandResponse(output=INVALID_DATE_FORMAT_TEMPLATE)

    notion_client, gcal_client = NotionClient(), GCalClient()

    user_page = notion_client.find_user_by_discord_id(discord_id=request.userId)
    if not user_page or 'email' not in user_page:
        return dto.CommandResponse(output=USER_NOT_FOUND_TEMPLATE)

    gcal_client.add_vacation_event(
        user_email=user_page['email'],
        start_date=start_date,
        end_date=end_date,
        event_title="Vacation"
    )

    now_kyiv = datetime.now(survey.TZ_KYIV)
    time_str = now_kyiv.strftime("%H:%M")
    body = SUCCESS_TEMPLATE.format(start_date=start_date.strftime('%Y-%m-%d'), end_date=end_date.strftime('%Y-%m-%d'))
    footer = FOOTER_TEMPLATE.format(channel=request.channelId, time=time_str)
    return dto.CommandResponse(output=f"{body}\n{footer}")
