# Task 16 — Typed payload/response models

Summary
- Introduce `BotRequestPayload` and `RouterResponse` (dataclasses or Pydantic) and validate at the `AppRouter` boundary.

Steps
- Define models with required/optional fields and minimal coercion (e.g., `userId`, `channelId`, `command`, `result`).
- Parse/validate inputs before dispatch; convert router outputs to `RouterResponse`.
- Map validation errors to user-safe messages and structured logs.

Acceptance Criteria
- `AppRouter.dispatch` accepts `BotRequestPayload` and returns `RouterResponse`.
- Invalid inputs fail fast with clear logs; no ambiguous KeyErrors.

Validation
- Unit tests for model validation; run `pytest -q`.

Testing Note
- Tests must read payloads from `payload_examples.txt` and responses from `responses`.

Behavior Constraints
- Do not change Discord behavior: user-visible messages, mentions, reactions, component IDs/layout, ephemeral/public status, and message edit/delete timing must remain identical.
