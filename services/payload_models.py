from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, Optional


@dataclass
class BotRequestPayload:
    """Validated payload for router.dispatch input."""

    channelId: str
    userId: Optional[str] = None
    sessionId: Optional[str] = None
    command: Optional[str] = None
    type: Optional[str] = None
    status: Optional[str] = None
    message: Optional[str] = None
    result: Dict[str, Any] = field(default_factory=dict)
    author: Optional[str] = None
    channelName: Optional[str] = None
    timestamp: Optional[int] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BotRequestPayload":
        """Validate and construct BotRequestPayload from a raw dict.

        Required fields depending on intent:
        - channelId: always required
        - command: required for command-driven payloads (most cases). If type=="mention"
          and command is missing, default to "mention" for routing convenience.
        - userId and sessionId: required for command payloads; sessionId must be a non-empty string.
          The session format is typically "{channelId}_{userId}" but we only warn via ValueError
          if it is missing; format enforcement should be done at the producer boundary.
        """
        # channelId is always required
        channel_id_raw = data.get("channelId")
        channel_id = str(channel_id_raw) if channel_id_raw is not None else ""
        if not channel_id:
            raise ValueError("channelId is required")

        # Determine command/type intent
        cmd = data.get("command")
        typ = data.get("type")
        if not cmd and typ == "mention":
            # Allow mention via type and normalize to a command for routing
            cmd = "mention"

        # For most payloads a command must be present
        if not cmd or not isinstance(cmd, str) or not cmd.strip():
            raise ValueError("command is required")

        # Require userId and sessionId for command payloads
        user_id_raw = data.get("userId")
        user_id = str(user_id_raw) if user_id_raw is not None else ""
        if not user_id:
            raise ValueError("userId is required")

        session_id_raw = data.get("sessionId")
        session_id = str(session_id_raw) if session_id_raw is not None else ""
        if not session_id:
            raise ValueError("sessionId is required")

        # Coerce/validate optional fields
        result = data.get("result") or {}
        if not isinstance(result, dict):
            raise ValueError("result must be an object")

        return cls(
            channelId=channel_id,
            userId=user_id,
            sessionId=session_id,
            command=cmd,
            type=typ,
            status=data.get("status"),
            message=data.get("message"),
            result=result,
            author=data.get("author"),
            channelName=data.get("channelName"),
            timestamp=data.get("timestamp"),
        )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class RouterResponse:
    """Canonical response model for router outputs."""

    output: Any
    survey: Optional[str] = None
    message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        data: Dict[str, Any] = {"output": self.output}
        if self.survey is not None:
            data["survey"] = self.survey
        if self.message is not None:
            data["message"] = self.message
        return data
