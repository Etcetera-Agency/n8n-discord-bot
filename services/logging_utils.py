from __future__ import annotations
import logging
import contextvars
from typing import Any, Callable, Awaitable, Dict

from config import logger as base_logger

# Context variable to store logging context across async calls
current_context: contextvars.ContextVar[Dict[str, Any]] = contextvars.ContextVar(
    "current_context", default={}
)


class ContextLogger(logging.LoggerAdapter):
    """Logger adapter injecting contextual fields into log records."""

    def process(self, msg, kwargs):
        context = current_context.get().copy()
        context.update(self.extra)
        context.update(kwargs.pop("extra", {}))
        kwargs["extra"] = context
        return msg, kwargs


def get_logger(step_name: str | None = None, payload: Dict[str, Any] | None = None, **extra: Any) -> ContextLogger:
    """Return a logger enriched with execution context."""

    ctx = {}
    if payload:
        ctx["session_id"] = payload.get("sessionId")
        ctx["user"] = payload.get("userId")
        ctx["channel"] = payload.get("channelId")
    if step_name:
        ctx["step_name"] = step_name
    ctx.update({k: v for k, v in extra.items() if v is not None})
    return ContextLogger(base_logger, ctx)


def wrap_handler(step_name: str, func: Callable[[Dict[str, Any]], Awaitable[Any]]):
    """Wrap an async handler with contextual logging."""

    async def wrapper(payload: Dict[str, Any]):
        ctx = {
            "session_id": payload.get("sessionId"),
            "user": payload.get("userId"),
            "channel": payload.get("channelId"),
            "step_name": step_name,
        }
        token = current_context.set(ctx)
        log = get_logger(step_name, payload)
        log.info("start")
        log.debug("payload", extra={"payload": payload})
        try:
            result = await func(payload)
            log.debug("response ready", extra={"output": result})
            log.info("done")
            return result
        except Exception:
            log.exception("failed")
            raise
        finally:
            current_context.reset(token)

    return wrapper


def wrap_survey_handler(step_name: str, func: Callable[[Any], Awaitable[Any]]):
    """Wrap an async survey handler that receives a typed SurveyEvent.

    The wrapper extracts context from ``event.payload`` for consistent logging.
    """

    async def wrapper(event: Any):  # SurveyEvent at runtime
        payload = getattr(event, "payload", None)
        ctx = {
            "session_id": getattr(payload, "sessionId", None) if payload else None,
            "user": getattr(payload, "userId", None) if payload else None,
            "channel": getattr(payload, "channelId", None) if payload else None,
            "step_name": step_name,
        }
        token = current_context.set(ctx)
        log = get_logger(step_name, payload.to_dict() if payload else None)
        log.info("start")
        if payload:
            log.debug("payload", extra={"payload": payload.to_dict()})
        try:
            result = await func(event)
            log.debug("response ready", extra={"output": result})
            log.info("done")
            return result
        except Exception:
            log.exception("failed")
            raise
        finally:
            current_context.reset(token)

    return wrapper
