# Task 20 — Rate limiting and retries

Summary
- Add simple rate-limit/backoff wrappers for Notion and webhook calls; surface friendly messages.

Steps
- Implement retry with exponential backoff; cap attempts.
- Handle 429/5xx with user-safe messages via `Strings`.

Acceptance Criteria
- Transient failures recover; user gets clear feedback when limits reached.

Validation
- Simulate failures; confirm backoff behavior and outputs. Run `pytest -q`.

Testing Note
- Tests remain fixture-based; do not hardcode payloads.

Behavior Constraints
- Do not change Discord behavior: user-visible messages, mentions, reactions, component IDs/layout, ephemeral/public status, and message edit/delete timing must remain identical.
