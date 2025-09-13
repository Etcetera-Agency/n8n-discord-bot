from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional
from datetime import datetime, timezone


@dataclass(frozen=True)
class SurveyStep:
    """Represents a single survey step."""

    name: str
    description: Optional[str] = None


@dataclass(frozen=True)
class SurveyResult:
    """Typed result captured for a survey step."""

    step_name: str
    value: Any
    recorded_at: datetime = datetime.now(timezone.utc)


@dataclass(frozen=True)
class SurveyEvent:
    """Typed container passed to survey step handlers.

    Includes the current step, its parsed result, and the original
    normalized bot request payload for auxiliary fields like author,
    channelId, timestamp, etc.
    """

    step: SurveyStep
    result: SurveyResult
    # Deferred import type to avoid a hard dependency loop
    payload: "services.payload_models.BotRequestPayload"  # type: ignore[name-defined]

