# Plan for Refactoring Survey Flow (surveyfix_tasks.md)

This document outlines the plan to refactor the Discord bot's survey flow based on the new requirements.

> **IMPORTANT:**
> - All payloads sent to n8n (including command names, prefixes, and structure) must remain strictly unchanged.
> - All logic related to Discord message deletions and reactions must remain strictly unchanged.
> - All logic related to slash commands must remain strictly unchanged.
> - Do **not** modify these aspects during any refactoring.
> - After each change, verify that n8n receives the exact same payloads and that Discord message deletion/reaction logic and slash commands logic is unaltered.
- use strings from commands from strings.py for survey
- ALSWAYS use same_name_slash_commands inputs  for user input for survey. THEY MUST BE CONSISTENT


**Guiding Principles:**
*   **Don't Break Functionality:** Test frequently during changes.
*   **KISS:** Keep solutions simple and direct.
*   **DRY:** Eliminate duplicated code.

## Goals

1.  Modify the survey initiation logic to handle existing sessions and channel checks correctly.
2.  Standardize the step progression: Question -> "Ввести" Button -> Modal -> Local Storage.
3.  Ensure only the specified steps (`workload_today`, `workload_nextweek`, `connects`, `dayoff_nextweek`) are included, in that exact order.
4.  Send final webhook with all collected data at the end, ensuring the payload structure matches the current implementation.
5.  Refactor message handling to delete previous step messages and provide user feedback after each step.

## Affected Files

*   `bot/commands/survey.py`: Major changes to survey start, step handling, interaction responses.
*   `services/survey.py`: Potential minor adjustments to `SurveyFlow` state management.
*   `services/webhook.py`: Ensure webhook function can return n8n response content.
*   `bot/views/`: Need to create/modify modals for each step type. Existing views (`workload.py`, `day_off.py`) might be deprecated or heavily refactored if modals replace direct button interactions for answers.
*   `config/strings.py`: Update button labels, modal titles, messages.
*   `config/constants.py`: Define the required step list/order explicitly.

## Detailed Plan

### 1. Survey Initiation (`handle_start_daily_survey` / Button Callback)


[✔] **Check Existing Session:**
    [✔] When the "Start Survey" button is clicked, use `survey_manager.get_survey(session_id)`.
    [✔] If a `SurveyFlow` object exists:
        [✔] Get the `current_step()`.
        [✔] Call `ask_dynamic_step` for that step (effectively resending the question/button for the step the user was last on).
    [✔] If no survey exists: Proceed to channel check.
[✔] **Channel Check & Step Handling:**
    [✔] Call `check_channel` webhook.
    [✔] If response is `true` and `steps` are provided:
        [✔] Filter the received `steps` to *only* include `["workload_today", "workload_nextweek", "connects", "dayoff_nextweek"]`.
        [✔] Sort the filtered steps into the exact order: `["workload_today", "workload_nextweek", "connects", "dayoff_nextweek"]`.
        [✔] If the resulting list is empty, send `SURVEY_COMPLETE_MESSAGE`.
        [✔] Otherwise, call `survey_manager.create_survey` with the filtered/ordered steps.
        [✔] Call `ask_dynamic_step` for the first step.
    [✔] If response is `true` but NO `steps`: Send `SURVEY_COMPLETE_MESSAGE`.
    [✔] If response is `false`: Log a warning (channel not registered).
### 2. Step Presentation (`ask_dynamic_step`)

[✔] **Standardize Message:》
    [✔] Remove logic for sending different view types (workload buttons, day_off buttons).
    [✔] Always send a single message containing:
        [✔] The step-specific question text (e.g., "Скільки годин...").
        [✔] A single `discord.ui.Button` with the label "Ввести" and a unique `custom_id` (e.g., `f"survey_step_{survey.session_id}_{step_name}"`).
    [✔] Store the `id` of this sent message in the `SurveyFlow` object (e.g., `survey.current_step_message`).

[✔] ### 3. Interaction Handling ("Ввести" Button Callback)

[✔] **Identify Button Click:** Use a persistent view or bot event listener to catch clicks on buttons with `custom_id` matching the pattern `survey_step_*`.
[✔] **Show Modal:**
    [✔] Inside the button callback:
        [✔] Retrieve the relevant `SurveyFlow` object using channel context
        [✔] Verify the interaction occurred in the correct survey channel
        [✔] Create the appropriate modal based on the `step_name` from the `custom_id`.
    [✔] Use `interaction.response.send_modal(modal)`.

### 4. Modal Implementation & Submission (`on_submit` in Modals)

[✔] **Create Modals:** Define `discord.ui.Modal` classes for each step type (`WorkloadTodayModal`, `WorkloadNextWeekModal`, `ConnectsModal`, `DayOffNextWeekModal`). Each modal will have the appropriate `discord.ui.TextInput`.
    [✔] WorkloadTodayModal implemented with submit handler
    [✔] WorkloadNextWeekModal implemented with submit handler
    [✔] ConnectsModal implemented
    [✔] DayOffNextWeekModal implemented with submit handler
[✔] **Modal `on_submit` Logic:**
    1.  [✔] Input validation performed
    2.  [✔] Response deferred properly
    3.  [✔] Results stored in survey object
    4.  [✔] Original question message deleted
    5.  [✔] Confirmation message sent
    6.  [✔] Survey advanced to next step
    7.  [✔] Completion checked
        *   [✔] If **not done**: Call `await continue_survey(interaction.channel, survey)` to ask the next question.
        *   [✔] If **done**: Call `await finish_survey(interaction.channel, survey)` to send the final results to n8n.

### 5. Webhook Communication (`finish_survey`)

*   This function is called only after the *last* step's modal is submitted.
[✔] It gathers all results stored in `survey.results`.
[✔] It constructs the **single, final payload** exactly as the current implementation does (likely with `command: "survey"`, `status: "complete"`, `userId`, `channelId`, `sessionId`, and the complete `result` dictionary containing all answers).
[✔] It calls `webhook_service.send_webhook_with_retry` to send this final payload to n8n.
[✔] It handles the response from n8n (e.g., displaying a final message to the user).
[✔] It calls `survey_manager.remove_survey(survey.user_id)` to clean up the completed survey session.

### 6. Cleanup (`finish_survey`, `continue_survey`)
 
*   [✔] `continue_survey`:** This function remains simple: gets `survey.current_step()` and calls `ask_dynamic_step` to display the next question/button.
*   [✔] `finish_survey`:** This function is now crucial. It's called *only* after the last step is answered. Its primary role is to compile all results and send the single, final webhook to n8n as described in Step 5. It also handles the final user feedback and survey cleanup.

### 7. Configuration

*   [✔] `config/constants.py`:** Define `REQUIRED_SURVEY_STEPS = ["workload_today", "workload_nextweek", "connects", "dayoff_nextweek"]`.
*    [✔] `config/strings.py`:** Add/update strings for modal titles, button labels, new messages.

## Flow Diagram (Mermaid)

```mermaid
sequenceDiagram
    participant User
    participant DiscordButton as "Start Survey Button"
    participant BotLogic as "Bot Logic (survey.py)"
    participant SurveyManager as "SurveyManager (survey.py)"
    participant N8N as "n8n Webhook"
    participant DiscordUI as "Discord UI (Messages, Modals)"

    User->>+DiscordButton: Clicks "Start Survey"
    DiscordButton->>+BotLogic: Interaction received (user_id)
    BotLogic->>+SurveyManager: get_survey(user_id)
    alt Survey Exists
        SurveyManager-->>-BotLogic: Existing SurveyFlow
        BotLogic->>BotLogic: Get current_step()
        BotLogic->>DiscordUI: Send Question + "Ввести" Button (ask_dynamic_step)
        DiscordUI-->>User: Show Question + Button
    else Survey Does Not Exist
        SurveyManager-->>-BotLogic: None
        BotLogic->>+N8N: check_channel(channel_id)
        N8N-->>-BotLogic: Response (registered: true/false, steps: [...])
        alt Channel OK & Steps Provided
            BotLogic->>BotLogic: Filter & Sort steps to REQUIRED_SURVEY_STEPS
            BotLogic->>+SurveyManager: create_survey(user_id, channel_id, filtered_steps)
            SurveyManager-->>-BotLogic: New SurveyFlow
            BotLogic->>BotLogic: Get first step
            BotLogic->>DiscordUI: Send Question + "Ввести" Button (ask_dynamic_step)
            DiscordUI-->>User: Show Question + Button
        else Channel OK & No Steps
            BotLogic->>DiscordUI: Send SURVEY_COMPLETE_MESSAGE
            DiscordUI-->>User: Show "Survey Complete"
        else Channel Not Registered
            BotLogic->>BotLogic: Log warning
        end
    end

    loop For Each Step
        User->>+DiscordUI: Clicks "Ввести" Button
        DiscordUI->>+BotLogic: Interaction received (button click)
        BotLogic->>BotLogic: Verify user, get step_name
        BotLogic->>DiscordUI: interaction.response.send_modal(StepModal)
        DiscordUI-->>User: Show Modal
        User->>+DiscordUI: Submits Modal (user_input)
        DiscordUI->>+BotLogic: Interaction received (modal submit)
        BotLogic->>DiscordUI: Disable "Ввести" Button (edit original message)
        BotLogic->>DiscordUI: interaction.response.defer()
        BotLogic->>SurveyManager: survey.add_result(step_name, user_input)
        BotLogic->>DiscordUI: Delete original question message
        BotLogic->>DiscordUI: interaction.followup.send("Input saved.")
        DiscordUI-->>User: Show "Input saved."
        BotLogic->>SurveyManager: survey.next_step()
        BotLogic->>BotLogic: survey.is_done()?
        alt Not Last Step
            BotLogic->>BotLogic: continue_survey() -> ask_dynamic_step()
            BotLogic->>DiscordUI: Send Next Question + "Ввести" Button
            DiscordUI-->>User: Show next Question + Button
        else Last Step
            BotLogic->>BotLogic: finish_survey()
            BotLogic->>+N8N: Send FINAL Webhook (status: complete, results: {...})
            N8N-->>-BotLogic: Response (success, message)
            alt n8n Success
                 BotLogic->>DiscordUI: Send final message from n8n
                 DiscordUI-->>User: Show final message
            else n8n Error
                 BotLogic->>DiscordUI: Send error message
                 DiscordUI-->>User: Show error message
            end
            BotLogic->>SurveyManager: remove_survey(user_id)
            Note over BotLogic: Survey Complete
        end
    end
```

