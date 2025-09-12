# Task 06 — Minimal web auth for endpoints

Summary
- Protect `/start_survey` and `/debug_log` with a shared secret header `X-Auth-Token` (env: `WEB_AUTH_TOKEN`).

Steps
- In `web/server.py`, check header on protected routes; return 401 on missing/mismatch.
- Make token optional: if env is unset, allow requests (dev mode).
- Add small helper to validate header consistently.

Acceptance Criteria
- Requests without correct `X-Auth-Token` receive 401 when `WEB_AUTH_TOKEN` is set.

Validation
- Set `WEB_AUTH_TOKEN=abc` and curl: `curl -i -H 'X-Auth-Token: wrong' ...` -> 401.
- Run: `pytest -q tests/test_logging.py tests/test_survey_e2e.py`.

Testing Note
- Any tests for these routes should load payloads from `payload_examples.txt` and responses from `responses`.

