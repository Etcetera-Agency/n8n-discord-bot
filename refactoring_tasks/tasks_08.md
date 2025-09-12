# Task 08 — Enforce module boundaries

Summary
- Keep config, Discord, and services concerns in their packages without cross-leaks.

Steps
- Verify `config/` exports only config, constants, logger, strings.
- Ensure Discord-specific code lives in `discord_bot/` only.
- Ensure business logic lives in `services/` and is Discord-agnostic.

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
