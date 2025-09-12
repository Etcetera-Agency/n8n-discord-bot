# Task 21 — Remove legacy/unreachable branches

Summary
- Clean up dead code paths (e.g., router branches checking `payload["type"] == "mention"`).

Steps
- Identify unreachable conditionals and old branches in router/handlers.
- Remove or refactor to the current payload schema.

Acceptance Criteria
- Router/handlers contain only relevant, reachable logic.

Validation
- Run `rg -n "type\"\] == \"mention\"|legacy|TODO"` and review.
- `pytest -q` green.

Testing Note
- Tests should continue to read from `payload_examples.txt` and `responses`.

Behavior Constraints
- Do not change Discord behavior: user-visible messages, mentions, reactions, component IDs/layout, ephemeral/public status, and message edit/delete timing must remain identical.
