# Task 08 — Enforce module boundaries

Summary
- Keep config, Discord, and services concerns in their packages without cross-leaks.

Steps
- Verify `config/` exports only config, constants, logger, strings.
- Ensure Discord-specific code lives in `discord_bot/` only.
- Ensure business logic lives in `services/` and is Discord-agnostic.
- Create a new test (e.g., `tests/test_config_exports.py`) that scans project files for forbidden patterns such as `from config import WebhookService` or `from config import AppRouter`.
- Fail the test if any such import is detected.
- Document the rule in `AGENTS.md` or contributing docs so contributors know the restriction.

Acceptance Criteria
- No imports from `discord` under `services/`.
- No services re-exported by `config`.

Validation
- Search: `rg -n "from discord|import discord" services` should be empty.
- Run: `pytest -q`.

Testing Note
- Tests must use fixtures from `payload_examples.txt` and `responses`.

Behavior Constraints
- Do not change Discord behavior: user-visible messages, mentions, reactions, component IDs/layout, ephemeral/public status, and message edit/delete timing must remain identical.
