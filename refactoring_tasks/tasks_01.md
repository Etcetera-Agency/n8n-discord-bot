# Task 01 — Unify Entrypoint

Summary
- Make `main.py` the single start path. Move bot construction into a factory in `discord_bot/client.py`. Remove `main()` from `bot.py`. Ensure server starts once from `main.py`.

Steps
- Extract bot creation to `discord_bot/client.py:create_bot()` and export it.
- Update `main.py` to: create bot, start web server, start bot, handle lifecycle.
- Remove `async def main()` and `if __name__ == "__main__"` block from `bot.py`.
- Verify imports and remove any now-unused code.

Acceptance Criteria
- Running `python main.py` starts both Discord bot and web server.
- No entrypoint code remains in `bot.py`.
- No duplicate server starts.

Validation
- Run: `python main.py` locally; observe bot login and server bind.
- Run basic tests: `pytest -q`.

Testing Note
- Any new/updated tests must read payloads from `payload_examples.txt` and responses from `responses`.

