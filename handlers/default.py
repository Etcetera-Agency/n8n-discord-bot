"""Handler for unknown commands."""
import dto

DEFAULT_TEMPLATE = "Sorry, I didn't understand that command. Please try one of the available commands or use /help for more information."

def handle_default(request: dto.CommandRequest) -> dto.CommandResponse:
    """Handles any command that is not recognized."""
    return dto.CommandResponse(output=DEFAULT_TEMPLATE)
