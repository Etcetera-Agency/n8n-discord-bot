# Task 19 — Web server hardening

Summary
- Require `WEB_AUTH_TOKEN` on all write/trigger endpoints; protect or remove `/debug_log` in production.

Steps
- Enforce auth header on all non-read routes.
- Add size limits and content-type checks where appropriate.
- Hide `/debug_log` unless explicitly enabled.

Acceptance Criteria
- Unauthorized requests fail with 401; endpoints validate input.

Validation
- Curl endpoints with/without proper headers; confirm 401. Run `pytest -q`.

Testing Note
- Tests should load payload/response fixtures from repo files.

Behavior Constraints
- Do not change Discord behavior: user-visible messages, mentions, reactions, component IDs/layout, ephemeral/public status, and message edit/delete timing must remain identical.
