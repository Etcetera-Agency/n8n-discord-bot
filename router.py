"""
Maps incoming commands to their respective handlers.
"""
from typing import Callable, Dict, Any, Union
from dataclasses import asdict
import dto

# Import the actual handlers
from handlers import (
    register, unregister, check_channel, workload_today,
    workload_nextweek, day_off_thisweek, day_off_nextweek,
    connects_thisweek, vacation, survey, mention, default
)

HandlerResponse = Union[dto.CommandResponse, dto.SurveyResponse, dto.CheckChannelResponse]
Handler = Callable[[dto.CommandRequest], HandlerResponse]

# The dispatch map now points to the real, implemented handlers.
COMMAND_HANDLERS: Dict[str, Handler] = {
    "register": register.handle_register,
    "unregister": unregister.handle_unregister,
    "check_channel": check_channel.handle_check_channel,
    "workload_today": workload_today.handle_workload_today,
    "workload_nextweek": workload_nextweek.handle_workload_nextweek,
    "day_off_thisweek": day_off_thisweek.handle_day_off_thisweek,
    "day_off_nextweek": day_off_nextweek.handle_day_off_nextweek,
    "connects_thisweek": connects_thisweek.handle_connects_thisweek,
    "vacation": vacation.handle_vacation,
    "survey": survey.handle_survey,
    "mention": mention.handle_mention,
}

def route_command(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Parses the incoming payload, routes it to the correct handler,
    and returns the response as a dictionary.
    """
    try:
        request = dto.CommandRequest.from_dict(payload)
        command_name = request.command
    except (KeyError, TypeError):
        command_name = "default"
        request = dto.CommandRequest(command="unknown", channelId="unknown", userId="unknown")

    # Select the handler from the dispatch map, or use the default.
    handler = COMMAND_HANDLERS.get(command_name, default.handle_default)

    response_dto = handler(request)

    return asdict(response_dto)
