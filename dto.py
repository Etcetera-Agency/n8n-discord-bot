"""
Data Transfer Objects for requests and responses.
"""
from dataclasses import dataclass, field, asdict
from typing import List, Optional, Literal, Dict, Any

@dataclass
class Result:
    """Nested result object in the request payload, e.g., from a modal."""
    text: Optional[str] = None

@dataclass
class CommandRequest:
    """
    Represents the incoming request payload for a slash command.
    Strictly parsed from the webhook data.
    """
    command: str
    channelId: str
    userId: str
    result: Optional[Result] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CommandRequest":
        """Creates a CommandRequest from a dictionary, handling nested objects."""
        result_data = data.get("result")
        result = Result(text=result_data.get("text")) if isinstance(result_data, dict) else None

        for key in ["command", "channelId", "userId"]:
            if key not in data:
                raise KeyError(f"Missing required field in payload: {key}")

        return cls(
            command=data["command"],
            channelId=data["channelId"],
            userId=data["userId"],
            result=result,
        )

@dataclass
class CommandResponse:
    """A generic response for simple, non-survey commands."""
    output: str

@dataclass
class SurveyResponse:
    """Response for survey-related commands to control the flow."""
    output: str
    survey: Literal["continue", "end", "cancel"]
    url: Optional[str] = None

@dataclass
class CheckChannelResponse:
    """
    Response for the check_channel command.
    'output' must be a boolean as per requirements.
    """
    output: bool
    steps: List[str]

def to_dict(response_dto) -> Dict[str, Any]:
    """Converts a response DTO to a dictionary."""
    return asdict(response_dto)
