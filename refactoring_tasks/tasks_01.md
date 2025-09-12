# Task 01 — Remove stray/duplicate files (Completed)

Summary
- Remove accidental duplicates (e.g., files with spaces in names) and dead code.

Steps
- If present, delete `discord_bot/views/day_off 2.py` and any duplicates.
- Remove commented/unused imports in `bot.py` and elsewhere.
- Enforce no spaces in filenames under the repo.

Acceptance Criteria
- No file paths with spaces remain.
- Import graphs are clean; no unused imports flagged by linters.

Status
- Completed on Python 3.10. Lint is clean for F401/F841/E701/F811/E722/F821, and E402 handled (imports reordered or per-file ignored in tests). Test suite passes: 71/71.

Validation
- List files with spaces: `rg --files | rg ' '` and remove/rename as needed.
- Check common duplicate pattern: `rg --files | rg ' 2\\.py$'` (manual inspect).
- Run tests: `pytest -q`.

Testing Note
- Keep using `payload_examples.txt` and `responses` for test data; do not hardcode values.

Behavior Constraints
- Do not change Discord behavior: user-visible messages, mentions, reactions, component IDs/layout, ephemeral/public status, and message edit/delete timing must remain identical.
