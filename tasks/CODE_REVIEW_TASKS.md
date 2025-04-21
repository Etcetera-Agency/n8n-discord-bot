# Code Refactoring Tasks: n8n-discord-bot

> **IMPORTANT:**
> - All payloads sent to n8n (including command names, prefixes, and structure) must remain strictly unchanged.
> - All logic related to Discord message deletions and reactions must remain strictly unchanged.
> - Do **not** modify these aspects during any refactoring.
> - After each change, verify that n8n receives the exact same payloads and that Discord message deletion/reaction logic is unaltered.

**Guiding Principles:**
*   **Don't Break Functionality:** Test frequently during changes.
*   **KISS:** Keep solutions simple and direct.
*   **DRY:** Eliminate duplicated code.

---

## Phase 1: Critical Fixes & Setup

**Task 1: Fix `requirements.txt` Versions**
*   **Goal:** Ensure dependencies can be installed reliably.
*   **Action:**
    *   In `requirements.txt`, find the correct installable version for `aiohttp` (likely `3.9.x`, e.g., `aiohttp==3.9.5`). Update the line.
    *   In `requirements.txt`, find the correct installable version for `cachetools` (likely `5.3.x`, e.g., `cachetools==5.3.3`). Update the line.
*   **Verification:** Run `pip install -r requirements.txt` successfully.

**Task 2: Initialize `WebhookService` and Fix Static Calls (Interim)**
*   **Goal:** Make the bot runnable by resolving the static call error and setting up the intended webhook service.
*   **Action:**
    1.  In `main.py` or the main startup sequence (`bot.py` near the top), ensure the `services.WebhookService` is initialized *after* the `aiohttp.ClientSession` is ready (e.g., inside `on_ready` or similar async setup). Create a single instance and make it accessible, for example: `bot.webhook_service = WebhookService()` followed by `await bot.webhook_service.initialize()`.
    2.  Search `bot.py` for all calls like `ResponseHandler.handle_response(...)`.
    3.  Replace each call with `await bot.webhook_service.send_webhook(...)` (or potentially `send_interaction_response` or `send_button_pressed_info` depending on context).
    4.  Carefully adapt the arguments passed to match the parameters expected by the `WebhookService` methods. You may need to manually construct the `result` dictionary or pass `interaction`/`ctx` differently.
*   **Verification:** The bot should start without the `TypeError` related to calling `handle_response` statically. Basic webhook interactions should function.

---

## Phase 2: Consolidate Core Logic (DRY)

*(Tackle these one area at a time. Test related functionality after each task.)*

**Task 3: Consolidate Webhook/n8n Communication**
*   **Goal:** Use only `services.WebhookService` for all n8n interactions.
*   **Action:**
    1.  Delete the `ResponseHandler` class definition from `bot.py`.
    2.  Delete the global functions `send_webhook_with_retry`, `send_n8n_reply_channel`, `send_n8n_reply_interaction`, `send_button_pressed_info` from `bot.py`.
    3.  Search the entire project (`bot.py`, `bot/commands/*`) for any remaining calls to the deleted functions/class.
    4.  Ensure all webhook/n8n communication now exclusively uses methods from the `bot.webhook_service` instance created in Task 2 (e.g., `await bot.webhook_service.send_webhook(...)`, `await bot.webhook_service.send_interaction_response(...)`, `await bot.webhook_service.send_button_pressed_info(...)`).
*   **Verification:** All commands and interactions involving n8n webhooks must continue to work correctly using only `WebhookService`.

**Task 4: Consolidate UI Components (Views/Buttons/Selects)**
*   **Goal:** Use only the UI components defined in `bot/views/`.
*   **Action:**
    1.  Delete the duplicated view/component class definitions (`BaseView`, `WorkloadView`, `WorkloadButton`, `DayOffView`, `DayOffSelect`, `DayOffSubmitButton`, `GenericSelect`) from `bot.py` (approx. lines 416-562).
    2.  Delete the `create_view` factory function definition from `bot.py`.
    3.  Search the project (`bot.py`, `bot/commands/*`) for anywhere views are created.
    4.  Update these locations to import and use the classes and factory functions from the `bot/views/` directory (e.g., `from bot.views.factory import create_view`, `from bot.views.day_off import DayOffView`, etc.). Ensure the correct view/factory is used for each command.
*   **Verification:** All commands that use interactive components (buttons, selects) must display and function correctly using the components from `bot/views/`.

**Task 5: Consolidate Survey Management**
*   **Goal:** Use only `services.SurveyManager` and `services.SurveyFlow` for survey logic.
*   **Action:**
    1.  Delete the duplicated `SurveyFlow` class definition from `bot.py`.
    2.  Delete the global `SURVEYS` dictionary definition from `bot.py`.
    3.  Analyze the functions in `bot/commands/survey.py` (`handle_start_daily_survey`, `ask_dynamic_step`, `finish_survey`, etc.). Decide how to best integrate this logic:
        *   *Option A (Preferred):* Move the core logic into methods within the `services.SurveyManager` class.
        *   *Option B:* Create a new class (e.g., `SurveyCommands`) that uses `SurveyManager` and contains these functions as methods.
    4.  In the main startup sequence, create a single instance: `bot.survey_manager = SurveyManager()`.
    5.  Refactor all code related to starting, progressing, or checking surveys (e.g., in `on_message`, button callbacks, HTTP endpoint) to use methods of the `bot.survey_manager` instance (e.g., `bot.survey_manager.get_survey(user_id)`, `bot.survey_manager.create_survey(...)`, `await bot.survey_manager.ask_next_step(...)` [you might need to add methods like this]).
    6.  Remove or refactor the original functions from `bot/commands/survey.py` and `bot.py` once their logic is integrated.
*   **Verification:** Survey functionality (starting via HTTP, progressing through steps via buttons/modals, timing out) must work correctly using the centralized `SurveyManager`.

**Task 6: Consolidate Session Management**
*   **Goal:** Use only `services.SessionManager` for user session IDs.
*   **Action:**
    1.  Delete the global `sessions` `TTLCache` definition from `bot.py`.
    2.  Delete the global `get_session_id` function definition from `bot.py`.
    3.  In the main startup sequence, create a single instance: `bot.session_manager = SessionManager()`.
    4.  Search the project for any code that used the old `sessions` cache or `get_session_id` function.
    5.  Update these locations to use the `SessionManager` instance, primarily `bot.session_manager.get_session_id(user_id)`.
*   **Verification:** Session IDs should still be generated and included correctly in webhook payloads.

**Task 7: Consolidate Configuration & Constants**
*   **Goal:** Access all config and constants via the `config` module.
*   **Action:**
    1.  In `bot.py`, replace direct `os.getenv` calls for `DISCORD_TOKEN`, `N8N_WEBHOOK_URL`, `WEBHOOK_AUTH_TOKEN` with `Config.DISCORD_TOKEN`, `Config.N8N_WEBHOOK_URL`, `Config.WEBHOOK_AUTH_TOKEN` (import `Config` from `config.config`).
    2.  In the main startup sequence (e.g., `main.py` or top of `bot.py`), add a call to `Config.validate()`.
    3.  In `bot.py`, delete the duplicated `VIEW_TYPES` dictionary. Find where it was used and update the code to import and use `VIEW_CONFIGS` and `ViewType` from `config.constants` instead.
*   **Verification:** Bot should start, read config correctly, and use constants from the `config` module without errors.

**Task 8: Consolidate Logging**
*   **Goal:** Use the logging setup from `config/logger.py`.
*   **Action:**
    1.  In `bot.py`, delete the `logging.basicConfig(...)` call and the `logger = logging.getLogger(...)` line.
    2.  In the main startup sequence, call `setup_logging()` from `config.logger`. Store the returned logger instance (e.g., `log = setup_logging()`).
    3.  Replace uses of the old `logger` variable with the new `log` instance. Pass the `log` instance to classes/modules that need logging, if necessary.
*   **Verification:** Logging output should still be generated correctly using the configured setup.

---

## Phase 3: Refactor `bot.py` (Simplicity/SRP)

**Task 9: Clean up `bot.py`**
*   **Goal:** Make `bot.py` primarily responsible for initialization and orchestration, not detailed logic implementation.
*   **Action:**
    1.  Review `bot.py`. Ensure event handling logic (`on_ready`, `on_close`, `on_message`) is now fully contained within `bot.commands.EventHandlers` and that `bot.py` simply registers this handler.
    2.  Ensure command registration logic is fully contained within `bot.commands.PrefixCommands` and `bot.commands.SlashCommands`, and that `bot.py` simply instantiates these classes, passing the `bot` instance.
    3.  Ensure HTTP server logic (`run_server`, `start_survey_http`) is fully contained within `web/server.py`. Remove any related definitions or setup from `bot.py` (the `main()` function might coordinate starting the bot and server).
    4.  Remove any other leftover functions or classes that were consolidated in Phase 2.
*   **Verification:** `bot.py` should be significantly smaller. The bot must still start and all functionalities (events, commands, web server) must work correctly, being handled by their respective modules.

---

## Phase 4: Code Cleanup & Minor Improvements

**Task 10: Reduce Duplication in Commands**
*   **Goal:** Simplify command implementations by extracting common patterns.
*   **Action:**
    1.  Review the command implementations in `bot/commands/slash.py` (e.g., `vacation_slash`, `slash_connects_thisweek`).
    2.  Identify repeated sequences of actions (e.g., deferring interaction, adding reactions, calling webhook, handling success/error, updating message).
    3.  Extract these common sequences into private helper methods within the `SlashCommands` class or standalone helper functions if appropriate. Update the commands to call these helpers.
*   **Verification:** Commands should function identically, but their implementation code should be shorter and less repetitive.

**Task 11: Externalize User-Facing Strings (Optional/Lower Priority)**
*   **Goal:** Improve maintainability by moving hardcoded text out of the code.
*   **Action:**
    1.  Search the codebase for hardcoded user-facing strings (especially command descriptions, button labels, messages sent to users in Ukrainian).
    2.  Move these strings into `config/constants.py` or a new dedicated file (e.g., `config/strings.py`).
    3.  Update the code to import and use these constants instead of the hardcoded strings.
*   **Verification:** All UI text and bot messages should appear correctly, sourced from the constants file.

---