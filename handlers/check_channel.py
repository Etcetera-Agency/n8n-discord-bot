"""Handler for the 'check_channel' command."""
from datetime import datetime
import dto
from services import survey
from clients.postgres import PostgresClient

def handle_check_channel(request: dto.CommandRequest) -> dto.CheckChannelResponse:
    """
    Checks and returns the list of pending survey steps for the week.

    This handler determines the required survey steps and checks their
    completion status for the current week, returning a list of any
    steps that are still pending.
    """
    # This instantiation is a placeholder. In a real application,
    # the client would be provided through dependency injection.
    pg_client = PostgresClient()

    now_kyiv = datetime.now(survey.TZ_KYIV)
    week_start = survey.week_start_monday_00(now_kyiv)
    session_id = request.channelId

    # 1. Fetch latest status from the database.
    # The stubbed client returns None, so we default to an empty dict.
    weekly_status = pg_client.latest_weekly_status(
        session_id=session_id, week_start=week_start
    ) or {}

    # 2. Get the list of all required steps for the week from our config.
    required_steps = survey.REQUIRED_STEPS_FOR_WEEK()

    # 3. Use the survey service to determine which steps are pending.
    pending_steps = survey.get_pending_steps(required_steps, weekly_status, now_kyiv)

    # 4. Return the response DTO. The 'output' is always True for this command.
    return dto.CheckChannelResponse(output=True, steps=pending_steps)
