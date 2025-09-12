# Task 17 — Error taxonomy mapping

Summary
- Map service exceptions to user-safe messages and log appropriately.

Steps
- Define/confirm exceptions: `NotionError`, `CalendarError`, `WebhookError`.
- Map to messages in `Strings` and use consistent try/except in handlers.
- Ensure secrets never appear in logs.

Acceptance Criteria
- Errors are categorized and produce friendly, localized output.

Validation
- Force errors in Notion/webhook paths; verify outputs/logs. Run `pytest -q`.

Testing Note
- Tests use repository fixtures (`payload_examples.txt`, `responses`).

Behavior Constraints
- Do not change Discord behavior: user-visible messages, mentions, reactions, component IDs/layout, ephemeral/public status, and message edit/delete timing must remain identical.
