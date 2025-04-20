# Tasks for Verifying Survey Flow with Dedicated Modals (surveyfix_tasks2.md)

**Goal:** Ensure the survey flow correctly uses its dedicated modals (`WorkloadModal`, `ConnectsModal`, `DayOffModal` defined in `bot/commands/survey.py`) for input, while leaving slash commands and their original interaction methods (views/arguments) completely unchanged.

---

## Phase 1: Code Verification & Refinement (`bot/commands/survey.py`)

1.  **[ ] Verify Modal Definitions:**
    *   [ ] Confirm `WorkloadModal`, `ConnectsModal`, `DayOffModal` are correctly defined within `bot/commands/survey.py`.
    *   [ ] Ensure their `__init__` methods correctly accept the `survey` object and `step_name`.
    *   [ ] Verify input fields (`TextInput`) within each modal are configured correctly (labels, placeholders, validation if any).
2.  **[ ] Verify `ask_dynamic_step`:**
    *   [ ] Check the `button_callback` within `ask_dynamic_step`.
    *   [ ] Confirm it correctly identifies the appropriate modal class (`WorkloadModal`, `ConnectsModal`, `DayOffModal`) based on the `step_name`.
    *   [ ] Confirm it instantiates the modal correctly, passing the `survey` object and `step_name`.
    *   [ ] Confirm `interaction.response.send_modal(modal)` is called.
3.  **[ ] Verify Modal Submission Logic (`on_submit` / `handle_modal_submit`):**
    *   [ ] Review the `on_submit` methods of the modals and the `handle_modal_submit` function they call.
    *   [ ] **Input Validation:** Ensure input validation (e.g., workload hours, connects is digit, dayoff not empty) happens correctly within `handle_modal_submit` using the `validate_fn`.
    *   [ ] **Survey Context Checks:** Verify checks for `interaction.user.id == survey.user_id` and `interaction.channel.id == survey.channel_id`.
    *   [ ] **Deferral:** Confirm `interaction.response.defer(ephemeral=True, thinking=False)` is called.
    *   [ ] **Result Storage:** Verify `survey.add_result(self.step_name, input_field.value)` correctly stores the data.
    *   [ ] **Message Cleanup:**
        *   Verify the logic attempts to fetch the original question message using `survey.current_question_message_id`.
        *   Verify it attempts to disable the button on the fetched message.
        *   Verify it attempts to delete the fetched message.
        *   Ensure `discord.NotFound` errors during cleanup are handled gracefully (logged as warning, process continues).
    *   [ ] **Confirmation:** Confirm `interaction.followup.send("Input saved.", ephemeral=True)` is called.
    *   [ ] **Survey Advancement:** Verify `survey.next_step()` is called.
    *   [ ] **Continuation/Completion:** Verify `continue_survey` or `finish_survey` is called based on `survey.is_done()`.
    *   [ ] **Error Handling:** Ensure the `try...except` block correctly catches errors during submission and attempts to send an error message to the user.
4.  **[ ] Verify `handle_start_daily_survey`:**
    *   [ ] Confirm the logic for checking existing surveys, checking channel registration, filtering/ordering steps (`REQUIRED_SURVEY_STEPS`), creating the `SurveyFlow` object, and calling `ask_dynamic_step` for the first step is correct and streamlined (no duplicate checks).
5.  **[ ] Verify `finish_survey`:**
    *   [ ] Double-check the final webhook payload structure (`command: "survey"`, `status: "complete"`, `result` dictionary, IDs) matches requirements precisely.
    *   [ ] Ensure `survey_manager.remove_survey` is called appropriately upon completion or error.
6.  **[ ] Verify `handle_survey_incomplete`:**
    *   [ ] Check the webhook payload (`command: "survey"`, `status: "incomplete"`, `result={"incompleteSteps": ...}`) is correct.
    *   [ ] Ensure `survey_manager.remove_survey` is called.

---

## Phase 2: Testing & Verification

1.  **[ ] Survey Flow Testing:**
    *   [ ] Test the complete survey cycle (`/start_survey` or button trigger).
    *   [ ] Verify each step presents the correct question and the "Ввести" button.
    *   [ ] Verify clicking "Ввести" shows the correct **survey-specific** modal.
    *   [ ] Verify submitting valid data in the modal proceeds correctly (saves data, cleans up message, confirms, advances).
    *   [ ] Verify submitting invalid data shows an ephemeral error message and does *not* advance the survey.
    *   [ ] Verify the final `finish_survey` webhook payload is correct.
    *   [ ] Test resuming an interrupted survey (e.g., restart bot mid-survey).
    *   [ ] Test survey timeout and verify the `incomplete` webhook payload.
2.  **[ ] Slash Command Testing (Regression):**
    *   [ ] Test `/workload_today`. Verify it uses its **original button View** interaction and sends its correct webhook payload. **Confirm it does NOT use the survey modal.**
    *   [ ] Test `/workload_nextweek`. Verify it uses its **original button View** interaction and sends its correct webhook payload. **Confirm it does NOT use the survey modal.**
    *   [ ] Test `/day_off_thisweek`. Verify it uses its **original button View** interaction and sends its correct webhook payload. **Confirm it does NOT use the survey modal.**
    *   [ ] Test `/day_off_nextweek`. Verify it uses its **original button View** interaction and sends its correct webhook payload. **Confirm it does NOT use the survey modal.**
    *   [ ] Test `/connects`. Verify it uses its **original argument-based** interaction and sends its correct webhook payload. **Confirm it does NOT use the survey modal.**
    *   [ ] Test `/vacation`. Ensure it remains unaffected and works correctly.
3.  **[ ] Edge Cases & Error Handling:**
    *   [ ] Test webhook failures during survey steps. Verify user feedback.
    *   [ ] Test permissions issues (e.g., bot can't delete messages during survey cleanup). Verify errors are logged but survey attempts to continue.
    *   [ ] Test modal timeouts during the survey.

---

## Phase 3: Documentation & Cleanup

1.  **[ ] Code Comments:** Ensure code in `bot/commands/survey.py` related to modals and their handling is well-commented.
2.  **[ ] Remove Unused Code (If Any):** Double-check for any remnants of the incorrect refactoring attempts (e.g., unused imports, context variables if they snuck back in).