# Task 14: Logging Integration

## Goal
Integrate detailed logging for all migrated n8n logic so it appears in the bot's existing log output.

## Requirements
- Reuse the project's configured logger (`from config.logger import logger` or `logging.getLogger('discord_bot')`).
- Log every significant step: incoming payload, external requests (Notion, calendar, HTTP), decisions, and final responses.
- Include contextual fields (`session_id`, `step_name`, user, channel) to trace execution across steps.
- Ensure errors are captured with stack traces via `logger.exception`.

## Pseudocode
```python
import logging
from config.logger import logger  # already writes to console and logs/server.log

async def handle_step(payload):
    session = payload["sessionId"]
    logger.info("start", extra={"session_id": session, "step": "workload_today"})
    try:
        logger.debug("query Notion", extra={"channel": payload["channelId"]})
        # ... perform logic ...
        logger.debug("response ready", extra={"output": result})
        logger.info("done", extra={"session_id": session})
        return result
    except Exception:
        logger.exception("failed", extra={"session_id": session})
        raise
```

## Testing
- **Unit tests**: use `caplog` or read `logs/server.log` to confirm expected log messages for success and error paths.
- **End-to-end tests**: run representative flows and verify that the log file contains entries for each processed step, capturing inputs, actions, and outputs.
- All tests must write their own inputs, steps, and outputs to a log file for later review.