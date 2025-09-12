# Task 10 — Consolidate views and factory

Summary
- Remove duplicated survey vs slash views; factor shared logic into generic components and a small factory.

Steps
- Identify duplicated classes across `discord_bot/views/*_slash.py` and `*_survey.py`.
- Extract shared pieces to `views/generic.py` or `views/components.py`.
- Ensure `views/factory.py` can build dynamic views for both contexts.

Acceptance Criteria
- No duplicated view classes for identical UI.
- `factory.create_view()` covers all supported commands/steps.

Validation
- Manual: trigger buttons/selects for workload/day off flows.
- Run: `pytest -q` UI-related tests (if any).

Testing Note
- Tests must load fixtures from `payload_examples.txt` and `responses`.

