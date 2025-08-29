"""Handler for direct mentions of the bot."""
import dto

MENTION_TEMPLATE = "Hello! If you need help, you can use the /survey command to check your status or see the available commands."

def handle_mention(request: dto.CommandRequest) -> dto.CommandResponse:
    """Handles direct mentions of the bot with a helpful message."""
    return dto.CommandResponse(output=MENTION_TEMPLATE)
