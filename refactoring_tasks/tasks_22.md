# Task 22 — Remove stray/duplicate files

Summary
- Remove accidental duplicates (e.g., files with spaces in names) and dead code.

Steps
- If present, delete `discord_bot/views/day_off 2.py` and any duplicates.
- Remove commented/unused imports in `bot.py` and elsewhere.
- Enforce no spaces in filenames under repo.

Acceptance Criteria
- No file paths with spaces remain.
- Import graphs are clean; no unused imports flagged by linters.

Validation
- List suspicious names: `rg -n "\\s\\w+\\.py$" -g '!venv'` and manual review.
- Run: `pytest -q`.

Testing Note
- Keep using `payload_examples.txt` and `responses` for test data; do not hardcode values.

Behavior Constraints
- Do not change Discord behavior: user-visible messages, mentions, reactions, component IDs/layout, ephemeral/public status, and message edit/delete timing must remain identical.

