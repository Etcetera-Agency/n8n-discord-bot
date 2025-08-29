"""
Main webhook entrypoint.

This module provides the main handler function that receives raw webhook
payloads, routes them to the appropriate command handler, and returns a
JSON-serializable response.
"""
from typing import Dict, Any
from dataclasses import asdict
import router
import dto

def process_webhook(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Main entrypoint for handling incoming webhook requests.
    """
    response_dict = {}
    try:
        if not isinstance(payload, dict) or "command" not in payload:
            raise ValueError("Invalid payload structure: must be a dict with a 'command' key.")

        # The router handles parsing, dispatch, and execution, returning a dict.
        response_dict = router.route_command(payload)

    except (ValueError, KeyError, TypeError) as e:
        # Handle bad payloads or parsing errors.
        print(f"ERROR: Invalid payload or command failed validation: {e}") # Placeholder for logging
        error_dto = dto.CommandResponse(output="There was a problem with your request. Please check the command and try again.")
        response_dict = asdict(error_dto)

    except Exception as e:
        # Handle all other unexpected errors during command execution.
        print(f"FATAL ERROR: Unexpected error processing webhook: {e}") # Placeholder for logging
        error_dto = dto.CommandResponse(output="An unexpected error occurred. The team has been notified.")
        response_dict = asdict(error_dto)

    return response_dict
