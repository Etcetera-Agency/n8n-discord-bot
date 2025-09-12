# Refactoring Plan — n8n Discord Bot

This plan proposes targeted improvements to structure, reliability, testability, and operability based on the current codebase.

## Goals

- Single, coherent entrypoint and lifecycle for Discord bot + web server
- Clear module boundaries and ownership (no cross‑package leaks)
- Robust survey flow with consistent state and fewer globals
- Smaller, focused modules and views with less duplication
- Safer web surface (authn, logging)
- Stronger typing and payload validation
- Faster, reproducible tests that follow repository fixtures

## Behavior Constraints

- Do not change Discord user-visible behavior during refactors.
- Preserve: message texts (via `config/strings.py`), mentions, reactions, component layout, custom_id/labels, ephemeral vs public responses, and edit/delete flow and timing (defer, followup vs original).
- Keep router payload/response shapes stable (e.g., `output`, `survey`, `url`, `next_step`).

## Key Observations (Current State)

- Duplicate entrypoints and lifecycle:
  - `bot.py` defines its own `main()` and also creates the bot; `main.py` starts the bot and server too.
- Config package leaks services:
  - `config/__init__.py` re‑exports `WebhookService` from `services.webhook`, creating circular coupling.
- Survey state mismatch in dispatcher:
  - `services/webhook.py` uses a `SURVEYS` dict keyed by user ID, but `services/survey.py:SurveyManager` stores by channel ID. Continuation code uses `userId` key -> potential KeyError/logic bug.
- Overlapping mention/command routing:
  - `bot.py:on_message` parses `!register/!unregister` manually; `services/router.parse_prefix()` already handles these.
- Monolithic Discord command file:
  - `discord_bot/commands/slash.py` is very large; hard to reason about and test in isolation.
- Views duplication/naming issues:
  - `discord_bot/views/day_off 2.py` looks accidental; multiple similar view classes across survey/slash.
- Web server exposes debug and survey start without auth.
- Tests already use `payload_examples.txt` and `responses` (great). Keep this contract for any new/updated tests.
 - Naming mismatch: `WebhookService` is not a true webhook; better represented as an in‑process router.

## Phase 0 — Quick Wins (1–2 days)

1) Unify entrypoint
- Make `main.py` the only executable entry. Remove `main()` from `bot.py`.
- Move bot construction to `discord_bot/client.py:create_bot()` and import in `main.py`.
- Ensure `web.create_and_start_server(bot)` runs once, owned by `main.py`.

2) Fix config/service coupling
- Remove `WebhookService` re‑export from `config/__init__.py`.
- Fix imports to use `from services.webhook import WebhookService, webhook_service`.

3) Survey continuation correctness
- In `services/webhook.py`: stop indexing `SURVEYS` by `userId`; use `channelId` or `survey_manager.get_survey(channel_id)` instead.
- Prefer a single source of truth: access state via `survey_manager`, not a copied dict.

4) Deduplicate mention handling
- In `bot.py:on_message`, drop manual `!register/!unregister` parsing.
- For messages mentioning the bot, call `WebhookService.send_webhook(..., command="mention")` and let `router.parse_prefix` handle prefix commands uniformly.

5) Remove stray/duplicate files
- Delete `discord_bot/views/day_off 2.py`.
- Confirm any dead code paths and remove commented/unused imports in `bot.py`.

6) Secure web endpoints (minimal)
- Add optional shared secret header `X-Auth-Token` for `/start_survey` and `/debug_log` (env: `WEB_AUTH_TOKEN`). Reject if missing or mismatched.

## Phase 1 — Boundaries, Structure, Ownership (3–5 days)

1) Module boundaries
- Config package contains only configuration and simple constants (no service imports/exports).
- Discord code (commands, views, client) lives under `discord_bot/` only.
- Business logic lives under `services/` and is Discord‑agnostic.

2) AppRouter (formerly WebhookService)
- Rename `WebhookService` to `AppRouter` to reflect in‑process dispatch.
- Introduce typed boundaries: `BotRequestPayload` (input) and `RouterResponse` (output) using dataclasses or Pydantic.
- Keep `AppRouter` pure: only build/validate/dispatch and return data; no UI/state side‑effects.
- Move survey “continue/cancel/end” handling to Discord handlers that call `survey_manager`.
- Keep all UI/Discord operations out of `services/` to avoid circular imports.

3) Slash command split into cogs
- Break `discord_bot/commands/slash.py` into cogs by domain: `workload.py`, `day_off.py`, `connects.py`, `vacation.py`, `register.py`, `survey.py`.
- Keep common helpers in `discord_bot/commands/utils.py`.

4) Views safety and minimal helpers
- Preserve separate survey vs slash views due to Discord flow constraints.
- Add only non-invasive helpers (constants/tiny functions) to avoid duplication.
- Keep `views/factory.py` as-is; extend cautiously only when strictly necessary.

5) Strings and i18n
- Keep user‑facing Ukrainian strings in `config/strings.py`. Add interpolation helpers; avoid inline f‑strings with logic in Discord handlers.

## Phase 2 — Survey Flow Hardening (3–4 days)

1) Single source of truth for survey state
- All state goes through `survey_manager`. No direct dict access from other modules.
- Keys by `channel_id` consistently. Ensure `StartSurveyView`/handlers use channel‑bound lookups.

2) Explicit survey model
- Add a light dataclass for survey payloads/results to improve clarity (`SurveyStep`, `SurveyResult`).
- Record `todo_url` and step outcomes explicitly; remove ad‑hoc dict manipulations.

3) Timeout and cleanup
- Ensure timeout task references the same state (by channel). Use `survey_manager.get_survey_by_session` only where session IDs are necessary.
- Centralize message cleanup in `SurveyFlow.cleanup()` and invoke from all completion/cancel paths.

## Phase 3 — Types, Validation, Errors (2–3 days)

1) Payload/response typing
- Add strong models for incoming payloads and router responses: `BotRequestPayload`, `RouterResponse`.
- Prefer dataclasses + manual validation or Pydantic if acceptable.
- Validate at the `AppRouter` boundary; convert to internal types early.

2) Error taxonomy
- Define service exceptions (`NotionError`, `CalendarError`, `WebhookError`) already exist; map them to user‑safe messages from `Strings`.
- Keep logging at WARN/ERROR with context; avoid leaking secrets.

3) Logging consistency
- Use `config.logger.setup_logging()` everywhere. Remove ad‑hoc loggers and duplicate initialization.
- Add structured context to logs via `services.logging_utils.current_context` (already present in router).

## Phase 4 — Security & Ops (2–3 days)

1) Web server hardening
- Require `WEB_AUTH_TOKEN` for all write/trigger endpoints; return 401 otherwise.
- Remove `/debug_log` in production or protect behind auth. Add size limits and content‑type.

2) Rate limiting and retries
- Add simple rate‑limit/backoff wrappers around Notion and web calls; propagate friendly messages to users.

## Phase 5 — Cleanup and Polish (ongoing)

- Normalize naming: prefer snake_case files, no spaces in filenames.
- Remove legacy/unreachable branches (e.g., `router` branch checking `payload["type"] == "mention"`).
- Document architecture boundaries in README with a simple diagram.

## Acceptance Criteria per Phase

Phase 0
- `python main.py` is the only start path; `bot.py` has no `main()`.
- `config` does not import or re‑export services.
- Survey continuation uses `survey_manager` lookups by channel ID.
- `/start_survey` rejects requests without `X-Auth-Token` when configured.

Phase 1
- Slash commands split into 5–6 cogs; imports simplified; no circulars.
- `AppRouter` (renamed from `WebhookService`) returns typed `RouterResponse`; no Discord/UI code in services.
- Views preserved; no functional changes to step-by-step flows; only accidental duplicates removed and minimal helpers added.

Phase 2
- Survey state transitions tested for continue/cancel/end, including timeout, using only `survey_manager`.

Phase 3
- Payloads validated; type errors surface early; logs are structured and non‑sensitive.

Phase 4
- Protected endpoints enforce auth; basic rate limiting/backoff in place.

## Test Strategy

- Continue using `payload_examples.txt` and `responses` for test fixtures. Do not hardcode payloads or responses in tests. If using typed models, parse strings from these files into `BotRequestPayload`/`RouterResponse` objects within the tests.
- Add targeted unit tests:
  - Router payload builder/dispatcher (now caller‑driven)
  - `services/router.dispatch` survey paths for continue/end/cancel
  - `discord_bot/views/start_survey.py` happy/error paths (with auth on `/start_survey`)
  - `services/survey.SurveyManager` transitions and cleanup
  - `config.config.Config.validate` failure modes

## Risk/Trade‑offs

- Splitting `slash.py` requires careful import wiring; mitigate by introducing one cog at a time.
- Tightening web auth may require updating n8n calls to include the header.
- Pydantic adds a dependency; keep optional or gated if footprint matters.

## Suggested Task Ordering (Backlog)

1. Remove `config` → services coupling; fix imports; delete `views/day_off 2.py`.
2. Make `main.py` the sole entry; move bot creation to `discord_bot/client.py` and patch `main.py`.
3. Fix survey continuation to use `survey_manager` by `channel_id` everywhere; remove side‑effects from `WebhookService`.
4. Add `WEB_AUTH_TOKEN` validation to web handlers; guard `/debug_log`.
5. Split `slash.py` into cogs; keep views separate and add minimal helpers only.
6. Add new tests that consume `payload_examples.txt` and `responses` only.
7. Introduce payload/response models (optional pydantic) and stricter logging.
8. Add basic rate limiting/backoff.

---

If you want, I can start with Phase 0 now (clean imports, fix survey continuation, and unify the entrypoint) and open a PR with minimal, well‑scoped changes plus tests that read from the shared fixtures.
