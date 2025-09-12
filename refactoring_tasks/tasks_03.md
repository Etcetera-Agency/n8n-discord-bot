# Task 03 — Unify Entrypoint (Completed)

Summary
- Make `main.py` the single start path. Provide a factory `discord_bot/client.py:create_bot()` that returns the configured bot instance built in `bot.py`. Ensure the web server and bot start from `main.py`.

Steps
- Added/updated factory `discord_bot/client.py:create_bot()` to return `bot.bot` (preserves prefixes, events, and handlers).
- Updated `main.py` to use `create_bot()` and start the web server and the bot.
- No `main()` or `__main__` guard existed in `bot.py`; no changes needed there for entrypoint removal.

Acceptance Criteria
- Running `python main.py` starts both the Discord bot and the web server.
- No entrypoint code remains in `bot.py` (confirmed; only definitions and setup).
- No duplicate server starts.

Status
- Completed on Python 3.10. Test suite passes: 71/71.

Validation
- Run: `python main.py` locally; observe bot login and server bind.
- Run tests: `pytest -q`.

Testing Note
- Any new/updated tests must read payloads from `payload_examples.txt` and responses from `responses`.

Behavior Constraints
- Do not change Discord behavior: user-visible messages, mentions, reactions, component IDs/layout, ephemeral/public status, and message edit/delete timing must remain identical.
- Router payload/response fields driving UI (`output`, `survey`, `url`, `next_step`) must remain stable.
