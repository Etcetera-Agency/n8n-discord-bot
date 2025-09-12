# Task 14 — Timeout and cleanup centralization

Summary
- Centralize survey timeout and cleanup logic to ensure consistent resource handling.

Steps
- Add `SurveyFlow.cleanup()` to handle UI/message cleanup.
- Ensure all completion/cancel/timeout paths call cleanup.
- Verify timeout task references same state source and correct keys.

Acceptance Criteria
- No orphaned buttons/messages after survey end/cancel/timeout.

Validation
- Simulate timeout; confirm cleanup runs. Run: `pytest -q tests/test_survey_e2e.py`.

Testing Note
- Continue using fixtures from `payload_examples.txt` and `responses`.

