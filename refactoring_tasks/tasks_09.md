# Task 09 — Split slash commands into cogs

Summary
- Break `discord_bot/commands/slash.py` into domain cogs.

Steps
- Create cogs: `workload.py`, `day_off.py`, `connects.py`, `vacation.py`, `register.py`, `survey.py`.
- Move command groups/handlers accordingly; keep shared helpers in `commands/utils.py`.
- Update bot setup to load these cogs.

Acceptance Criteria
- `slash.py` is removed or trimmed to loading cogs only.
- All slash commands function as before.

Validation
- Run: `python main.py` and exercise slash commands.
- Run focused tests: `pytest -q tests/test_survey_start.py tests/test_vacation.py`.

Testing Note
- Tests should keep using repository fixtures (`payload_examples.txt`, `responses`).

