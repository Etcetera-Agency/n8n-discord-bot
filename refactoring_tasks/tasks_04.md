# Task 04 — Deduplicate mention handling

Summary
- Stop parsing `!register/!unregister` in `on_message`. For mentions, send a `mention` request through the `AppRouter` and rely on routing.

Steps
- In `bot.py:on_message`, remove manual prefix parsing after a mention.
- Always call the router to handle mentions (e.g., `app_router.dispatch(...)`), not per‑message manual parsing.
- Keep reactions/placeholder message behavior consistent.

Acceptance Criteria
- Mention interactions handled once via router; no duplicate command paths.
- `!register/!unregister` via prefix commands still work through command handlers.

Validation
- Mention the bot with and without known commands and observe consistent behavior.
- Run: `pytest -q tests/test_check_channel.py tests/test_router.py`.

Testing Note
- Tests should continue to read fixtures from `payload_examples.txt` and `responses`.
