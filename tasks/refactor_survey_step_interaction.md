# Task: Refactor Survey Step Interaction

This task focuses on implementing the standardized per-step interaction pattern for the survey flow, ensuring each step follows the sequence: Initial message with button -> Button blocked & reaction added on click -> Modal for input -> Input saved & per-step webhook sent -> Initial message updated with n8n output, reaction/button removed -> Next step or completion.

**Important Considerations:**

*   The survey is bounded to the **channel**, not the user who clicks the button. Any user in the channel should be able to interact with the current survey step.
*   All payloads sent to n8n must remain strictly unchanged in structure and content, except for the data being sent for the specific step.
*   Existing slash command functionality must remain unaffected.
*   Message deletion and reaction logic should be handled as described in the plan.

**Affected Files:**

*   `discord_bot/commands/survey.py`
*   `services/survey.py`
*   `services/webhook.py`
*   `discord_bot/views/` (Modals)
*   `config/strings.py` / `config/constants.py`

**Steps:**

1.  **Analyze Current Survey Code:** Read `discord_bot/commands/survey.py` and `services/survey.py` to understand the current survey handling, step progression, and state management. Identify where user-specific checks for interactions might need to be removed or adjusted to be channel-bound.
2.  **Refine `SurveyFlow` and `SurveyManager`:**
    *   Modify `services/survey.py` to manage `SurveyFlow` instances keyed by `channel_id` instead of `user_id`.
    *   Update `SurveyManager` methods (`get_survey`, `create_survey`, `remove_survey`) to use `channel_id` as the primary key.
    *   Ensure the `SurveyFlow` object stores the `message.id` of the initial question message for the current step.
3.  **Refine `ask_dynamic_step`:**
    *   Modify this function in `discord_bot/commands/survey.py` to send the initial message for a step, containing the question text and a single "Ввести" button.
    *   Ensure the `custom_id` of the button includes the `channel_id` and `step_name` to identify the interaction context later.
    *   Store the `message.id` of this initial message in the channel's `SurveyFlow` object.
4.  **Implement "Ввести" Button Callback:**
    *   Create or modify the callback function that handles clicks on the "Ввести" button (identified by its `custom_id`).
    *   Retrieve the `SurveyFlow` object using the `interaction.channel.id`.
    *   Inside the callback:
        *   Immediately disable the button on the initial message using `interaction.message.edit(view=...)`.
        *   Add the "⏳" reaction to the initial message using `interaction.message.add_reaction("⏳")`.
        *   Present the appropriate modal for the current step using `interaction.response.send_modal(...)`. Ensure the modal is associated with the correct `SurveyFlow` instance (via channel ID).
5.  **Refine Modal Submission Handling (`on_submit` / `handle_modal_submit`):**
    *   Modify the logic in `discord_bot/commands/survey.py` that handles modal submissions.
    *   Retrieve the `SurveyFlow` object using the `interaction.channel.id`.
    *   After processing and validating the input:
        *   Send a webhook request to n8n for the *current step*. This webhook must include the `user_id` (from the interaction), `channel_id`, `session_id` (derived from channel/user or managed by `SessionManager`), `stepName`, and the collected `result` for this step.
        *   Wait for the webhook response from n8n.
        *   Retrieve the initial message using the stored `message.id` from the `SurveyFlow` object.
        *   Remove the "⏳" reaction from the initial message.
        *   Update the content of the initial message with the `output` received from the n8n webhook response.
        *   Remove the button from the initial message by editing its view.
        *   Handle cases where the message cannot be found or edited gracefully (e.g., log a warning).
        *   Advance the survey state (`survey.next_step()`).
        *   Check if the survey is complete (`survey.is_done()`). If not, call `ask_dynamic_step` for the next step in the same channel.
6.  **Update Configuration/Constants:**
    *   Review `config/strings.py` and `config/constants.py` for any strings or constants related to the survey flow and update them as needed (e.g., button labels, modal titles).