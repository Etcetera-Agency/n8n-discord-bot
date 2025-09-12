# Task 23 — Document architecture boundaries

Summary
- Update README with a simple diagram and clarify boundaries between `discord_bot`, `services`, and `web`.

Steps
- Add a brief diagram (ASCII or image under `assets/`).
- Document ownership and direction of dependencies.

Acceptance Criteria
- README explains architecture and module boundaries succinctly.

Validation
- Render README locally; ensure clarity.

Testing Note
- No test changes required; if added, use repo fixtures.

Behavior Constraints
- Do not change Discord behavior: user-visible messages, mentions, reactions, component IDs/layout, ephemeral/public status, and message edit/delete timing must remain identical.
