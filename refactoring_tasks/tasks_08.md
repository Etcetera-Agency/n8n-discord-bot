# Task 08 — Introduce AppRouter (rename WebhookService)

Summary
- Rename `WebhookService` to `AppRouter` and keep it pure: build/validate/dispatch only. Move UI/state side-effects to Discord handlers.

Steps
- Rename file/class: `services/webhook.py -> services/app_router.py` (`WebhookService -> AppRouter`). Keep a thin import alias temporarily if needed.
- Add typed boundaries: `BotRequestPayload` (input), `RouterResponse` (output) using dataclasses or Pydantic.
- Remove survey side-effects (continue/cancel/end) from the router; return flags/data to callers.
- Update imports across the codebase to use `AppRouter` and adapt calls (e.g., `app_router.dispatch(...)`).

Acceptance Criteria
- `services/` contains no Discord UI code (`add_reaction`, `send`, etc.).
- `AppRouter.dispatch` returns typed `RouterResponse` and does not mutate Discord state.
- Callers (commands/views) handle survey transitions via `survey_manager`.

Validation
- Grep for Discord API usage inside `services/` — should be none.
- Run: `pytest -q` relevant survey tests.

Testing Note
- Use `payload_examples.txt` and `responses` in any new tests.
