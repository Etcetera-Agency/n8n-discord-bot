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
        # Minimal validation of required fields
        channel_id = data.get("channelId")
        if not channel_id:
            raise ValueError("channelId is required")
        # Fill defaults for optional fields
        return cls(
            channelId=str(channel_id),
            userId=data.get("userId"),
            sessionId=data.get("sessionId"),
            command=data.get("command"),
            type=data.get("type"),
            status=data.get("status"),
            message=data.get("message"),
            result=data.get("result") or {},
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

