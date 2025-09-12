# Task 12 — Single survey state source

Summary
- Route all survey state reads/writes through `survey_manager`, keyed by channel where appropriate.

Steps
- Remove any direct dict access to survey state outside `survey_manager`.
- Ensure consistent keying (prefer `channel_id`) across handlers and services.
- Update start/continue/end paths to use the same retrieval method.

Acceptance Criteria
- One authoritative store for survey state with consistent keys.

Validation
- End-to-end survey run with continue/cancel/end works.
- `pytest -q tests/test_survey_steps_db.py tests/test_survey_start.py` pass.

Testing Note
- Tests read payloads/responses from repository fixtures.

