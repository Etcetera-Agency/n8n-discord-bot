from __future__ import annotations

from typing import Any, Dict, Type

from config import Strings
from services.logging_utils import get_logger

try:
    # Import error types directly from their modules to avoid circular imports
    from services.notion_connector import NotionError  # type: ignore
except Exception:  # pragma: no cover - optional at import time in some tests
    class NotionError(Exception):
        pass

try:
    from services.calendar_connector import CalendarError  # type: ignore
except Exception:  # pragma: no cover
    class CalendarError(Exception):
        pass

try:
    from services.webhook import WebhookError  # type: ignore
except Exception:  # pragma: no cover
    class WebhookError(Exception):
        pass


# Mapping of exception types to user-facing messages
EXCEPTION_MESSAGE_MAP: Dict[Type[BaseException], str] = {
    NotionError: Strings.TRY_AGAIN_LATER,
    CalendarError: Strings.TRY_AGAIN_LATER,
    WebhookError: Strings.TRY_AGAIN_LATER,
}


def map_exception_to_message(exc: BaseException) -> str:
    """Convert a known exception into a user-facing message.

    Unknown exceptions fall back to a safe generic message.
    """

    for etype, message in EXCEPTION_MESSAGE_MAP.items():
        if isinstance(exc, etype):
            return message
    return Strings.TRY_AGAIN_LATER


def log_exception_categorized(exc: BaseException, **context: Any) -> None:
    """Log an exception with a category and sanitized context.

    The logger is enriched with the current context captured by
    services.logging_utils.get_logger(). Only non-sensitive fields should be
    provided in context (e.g., channel_id, user_id, step_name, inputs summary).
    """

    category = (
        "notion" if isinstance(exc, NotionError)
        else "calendar" if isinstance(exc, CalendarError)
        else "webhook" if isinstance(exc, WebhookError)
        else "unexpected"
    )
    log = get_logger(f"error.{category}")
    # Note: avoid logging raw exception args that may contain tokens
    log.exception("handler failed", extra={"category": category, **context})


def handle_exception(exc: BaseException, **context: Any) -> str:
    """Log a categorized exception and return a user-facing message."""

    log_exception_categorized(exc, **context)
    return map_exception_to_message(exc)
