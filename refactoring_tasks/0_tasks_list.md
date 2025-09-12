# Refactoring Tasks Checklist

Use this checklist to track progress. Each item links to a detailed task.

- [x] 01 — Remove stray/duplicate files (refactoring_tasks/tasks_01.md)
- [ ] 02 — Normalize naming (refactoring_tasks/tasks_02.md)
- [ ] 03 — Unify Entrypoint (refactoring_tasks/tasks_03.md)
- [ ] 04 — Remove config/service coupling (refactoring_tasks/tasks_04.md)
- [ ] 05 — Fix survey continuation (refactoring_tasks/tasks_05.md)
- [ ] 06 — Deduplicate mention handling (refactoring_tasks/tasks_06.md)
- [ ] 07 — Minimal web auth for endpoints (refactoring_tasks/tasks_07.md)
- [ ] 08 — Enforce module boundaries (refactoring_tasks/tasks_08.md)
- [ ] 09 — Introduce AppRouter (rename WebhookService) (refactoring_tasks/tasks_09.md)
- [ ] 10 — Split slash commands into cogs (refactoring_tasks/tasks_10.md)
- [ ] 11 — Views safety and minimal helpers (refactoring_tasks/tasks_11.md)
- [ ] 12 — Centralize strings/i18n (refactoring_tasks/tasks_12.md)
- [ ] 13 — Single survey state source (refactoring_tasks/tasks_13.md)
- [ ] 14 — Explicit survey models (refactoring_tasks/tasks_14.md)
- [ ] 15 — Timeout/cleanup centralization (refactoring_tasks/tasks_15.md)
- [ ] 16 — Typed payload/response models (refactoring_tasks/tasks_16.md)
- [ ] 17 — Error taxonomy mapping (refactoring_tasks/tasks_17.md)
- [ ] 18 — Logging consistency (refactoring_tasks/tasks_18.md)
- [ ] 19 — Web server hardening (refactoring_tasks/tasks_19.md)
- [ ] 20 — Rate limiting/retries (refactoring_tasks/tasks_20.md)
- [ ] 21 — Remove legacy/unreachable branches (refactoring_tasks/tasks_21.md)
- [ ] 22 — Document architecture boundaries (refactoring_tasks/tasks_22.md)

Note for all tasks: When adding or updating tests, load payloads from `payload_examples.txt` and sample responses from `responses` instead of hardcoding.

Global behavior constraint: Do not change Discord behavior (messages, reactions, component IDs/layout, ephemeral/public status, and message edit/delete timing must remain identical).
