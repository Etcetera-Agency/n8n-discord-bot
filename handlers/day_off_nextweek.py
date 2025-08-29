"""Handler for the 'day_off_nextweek' command."""
from datetime import datetime, timedelta
import dto
from services import survey
from clients.notion import NotionClient
from clients.gcal import GCalClient
from clients.postgres import PostgresClient

# Response Templates
USER_NOT_FOUND_TEMPLATE = "Your Discord ID is not found in our Notion database. Please contact an administrator to get your email set up."
INVALID_DATE_FORMAT_TEMPLATE = "Please use the format YYYY-MM-DD for the date."
DATE_OUT_OF_RANGE_TEMPLATE = "The specified date does not fall within next week."
SUCCESS_TEMPLATE = "Your day off on {date} has been scheduled. Enjoy your break!"
FOOTER_TEMPLATE = "#{channel}  •  {time}"

def handle_day_off_nextweek(request: dto.CommandRequest) -> dto.CommandResponse:
    """
    Handles scheduling a day off for the next week.
    """
    try:
        if request.result is None or request.result.text is None:
            raise ValueError("Missing input")
        day_off = datetime.strptime(request.result.text, "%Y-%m-%d").date()
    except ValueError:
        return dto.CommandResponse(output=INVALID_DATE_FORMAT_TEMPLATE)

    now_kyiv = datetime.now(survey.TZ_KYIV)
    next_week_start = (survey.week_start_monday_00(now_kyiv) + timedelta(days=7)).date()
    next_week_end = next_week_start + timedelta(days=6)
    if not (next_week_start <= day_off <= next_week_end):
        return dto.CommandResponse(output=DATE_OUT_OF_RANGE_TEMPLATE)

    notion_client, gcal_client, pg_client = NotionClient(), GCalClient(), PostgresClient()

    user_page = notion_client.find_user_by_discord_id(discord_id=request.userId)
    if not user_page or 'email' not in user_page:
        return dto.CommandResponse(output=USER_NOT_FOUND_TEMPLATE)

    gcal_client.add_day_off_event(user_email=user_page['email'], day_off=day_off, event_title="Day Off")

    pg_client.upsert_survey_step(session_id=request.channelId, step_name="day_off_nextweek", completed=True)

    time_str = now_kyiv.strftime("%H:%M")
    body = SUCCESS_TEMPLATE.format(date=day_off.strftime('%Y-%m-%d'))
    footer = FOOTER_TEMPLATE.format(channel=request.channelId, time=time_str)
    return dto.CommandResponse(output=f"{body}\n{footer}")
