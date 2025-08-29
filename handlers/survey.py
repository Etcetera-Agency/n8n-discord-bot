"""Handler for the 'survey' command."""
from datetime import datetime
import dto
from services import survey
from clients.postgres import PostgresClient

# In a real application, this would be dynamically generated or come from config.
SURVEY_END_URL = "https://example.com/survey-dashboard"

# Response Templates
SURVEY_START_TEMPLATE = "You have a few steps to complete. Let's start with `{step_name}`."
SURVEY_COMPLETE_TEMPLATE = "You have completed all your survey steps for the week. Great job!"

def handle_survey(request: dto.CommandRequest) -> dto.SurveyResponse:
    """
    Checks the user's survey status and either prompts for the next
    incomplete step or confirms completion with a link.
    """
    pg_client = PostgresClient()
    now_kyiv = datetime.now(survey.TZ_KYIV)
    week_start = survey.week_start_monday_00(now_kyiv)
    session_id = request.channelId

    weekly_status = pg_client.latest_weekly_status(session_id=session_id, week_start=week_start) or {}
    required_steps = survey.REQUIRED_STEPS_FOR_WEEK()
    pending_steps = survey.get_pending_steps(required_steps, weekly_status, now_kyiv)

    if not pending_steps:
        return dto.SurveyResponse(
            output=SURVEY_COMPLETE_TEMPLATE,
            survey="end",
            url=SURVEY_END_URL
        )
    else:
        next_step = pending_steps[0]
        return dto.SurveyResponse(
            output=SURVEY_START_TEMPLATE.format(step_name=next_step),
            survey="continue",
            url=f"https://example.com/survey/next_step?step={next_step}&sessionId={session_id}"
        )
