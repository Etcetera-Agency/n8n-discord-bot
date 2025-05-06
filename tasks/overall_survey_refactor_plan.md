# Overall Refactoring Plan: Standardized Survey Flow

This plan outlines the comprehensive approach to refactor the Discord bot's survey flow. It aims to implement a standardized per-step interaction pattern, integrate Notion task fetching at the end, remove excessive logging, and document the process in new task files, all while preserving existing slash command functionality.

**Important Considerations:**

*   The survey is bounded to the **channel**, not the user who clicks the button. Interaction handling should retrieve the survey based on the channel ID.
*   All payloads sent to n8n must remain strictly unchanged in structure and content, except for the data being sent for the specific step or the final completion.
*   Existing slash command functionality must remain unaffected.
*   Message deletion and reaction logic should be handled as described in the plan.
*   Error handling for the Notion API call is crucial.
*   Excessive logging should be removed or adjusted.

**Goals:**

1.  Implement the standardized per-step survey interaction: Initial message with button -> Button blocked & reaction added on click -> Modal for input -> Input saved & per-step webhook sent -> Initial message updated with n8n output, reaction/button removed -> Next step or completion.
2.  Implement the final survey completion logic: Send final webhook -> Receive Notion URL -> Fetch and display Notion tasks.
3.  Remove excessive logging throughout the survey and related code.
4.  Ensure existing slash command functionality remains unchanged.
5.  Create new markdown files in the `tasks` directory detailing the refactoring steps.

**Affected Files (Primary):**

*   `discord_bot/commands/survey.py`: Core logic for survey start, step handling, interaction responses, modal handling, and completion.
*   `services/survey.py`: `SurveyFlow` class for state management.
*   `services/webhook.py`: For sending webhooks and handling responses.
*   `services/notion_todos.py`: For fetching Notion tasks.
*   `discord_bot/views/`: Existing views might need review, new modals will be defined or modified.
*   `config/logger.py`: Ensure correct logging setup is used.
*   `config/strings.py` / `config/constants.py`: For messages, button labels, and step definitions.
*   `tasks/`: New files will be created here.

**Detailed Steps (Broken into Individual Tasks):**

This refactoring will be broken down into the following individual tasks, detailed in separate markdown files:
1.  **Refactor Survey Step Interaction** (`tasks/refactor_survey_step_interaction.md`):
    *   Analyze current survey code and adjust for channel-bound interactions.
    *   Refine `SurveyFlow` and `SurveyManager` to use `channel_id` as the key and store message IDs.
    *   Modify `ask_dynamic_step` to send the initial message with a button.
    *   Implement the "Ввести" button callback to disable the button, add a reaction, and show the modal.
    *   Refine modal submission handling to process input, send a per-step webhook, update the initial message with n8n output, remove the reaction/button, and advance the survey.
    *   Update relevant configuration and constants.

2.  **Implement Survey Finalization and Notion Fetching** (`tasks/implement_survey_notion_fetch.md`):
    *   Refine the `finish_survey` function to gather results and send the final webhook (`status: "end"`).
    *   Handle the final webhook response, sending the output message.
    *   Implement Notion task fetching using the provided URL, including error handling.
    *   Display fetched tasks or a fallback message.
    *   Clean up the survey state by removing it from the `SurveyManager`.
    *   Update relevant configuration and strings.

3.  **Clean Up Excessive Survey Logging** (`tasks/cleanup_survey_logging.md`):
    *   Review logging statements in survey-related files.
    *   Identify and remove or adjust excessive or redundant logs.
    *   Ensure critical errors are still logged appropriately.
    *   Verify the logging setup.

**Flow Diagram (Updated Survey Step):**
```mermaid
sequenceDiagram
    participant User
    participant BotLogic as "Bot Logic (survey.py)"
    participant DiscordUI as "Discord UI (Messages, Modals)"
    participant SurveyManager as "SurveyManager (services/survey.py)"
    participant WebhookService as "WebhookService (services/webhook.py)"
    participant N8N as "n8n Webhook"
    participant NotionService as "Notion_todos (services/notion_todos.py)"
    participant NotionAPI as "Notion API"

    %% Start Survey (Initial Trigger)
    User->>BotLogic: Start Survey (e.g., button click)
    BotLogic->>SurveyManager: get_survey(channel_id)
    alt Survey Exists for Channel
        SurveyManager-->>BotLogic: Existing SurveyFlow
        BotLogic->>BotLogic: Get current_step()
    else No Survey for Channel
        SurveyManager-->>BotLogic: None
        BotLogic->>N8N: check_channel(channel_id)
        N8N-->>BotLogic: Response (registered: true/false, steps: [...])
        alt Channel OK & Steps Provided
            BotLogic->>BotLogic: Filter & Sort steps
            BotLogic->>SurveyManager: create_survey(channel_id, steps)
            SurveyManager-->>BotLogic: New SurveyFlow
        else
            BotLogic->>DiscordUI: Send completion/error message
            DiscordUI-->>User: Show message
            return
        end
    end

    loop For Each Step
        %% Ask Step Question
        BotLogic->>DiscordUI: Send Question + "Ввести" Button (ask_dynamic_step)
        DiscordUI-->>User: Show Question + Button
        Note over BotLogic: Store message.id in SurveyFlow

        %% User Clicks Button
        User->>DiscordUI: Clicks "Ввести" Button
        DiscordUI->>BotLogic: Interaction received (button click)
        BotLogic->>DiscordUI: Disable Button (edit message)
        BotLogic->>DiscordUI: Add ⏳ reaction (edit message)
        BotLogic->>DiscordUI: Show Step Modal (send_modal)
        DiscordUI-->>User: Show Modal

        %% User Submits Modal
        User->>DiscordUI: Submits Modal (input)
        BotLogic->>BotLogic: Validate & Store Input (survey.add_result)
        BotLogic->>+WebhookService: send_webhook(step_payload)
        WebhookService->>+N8N: POST /webhook (status: step, stepName, result, user_id, channel_id, session_id)
        N8N-->>-WebhookService: Response {output: "...", survey: "continue"}
        WebhookService-->>-BotLogic: return success, response

        BotLogic->>DiscordUI: Remove ⏳ reaction (edit message)
        BotLogic->>DiscordUI: Update message content (edit message)
        BotLogic->>DiscordUI: Remove Button (edit message)
        BotLogic->>DiscordUI: Delete Modal message (if applicable)
        BotLogic->>SurveyManager: survey.next_step()
        BotLogic->>BotLogic: survey.is_done()?

        alt Not Last Step
            BotLogic->>BotLogic: continue_survey() -> ask_dynamic_step()
        else Last Step
            BotLogic->>BotLogic: finish_survey()
        end
    end

    %% Finish Survey
    BotLogic->>+WebhookService: send_webhook(final_payload)
    WebhookService->>+N8N: POST /webhook (status: end, results, user_id, channel_id, session_id)
    N8N-->>-WebhookService: Response {output: "...", survey: "end", url: "..."}
        WebhookService-->>-BotLogic: return success, response

    BotLogic->>DiscordUI: Send final output message
    DiscordUI-->>User: Show final output

    opt Notion URL exists
        BotLogic->>+NotionService: Instantiate Notion_todos(url, days=14)
        NotionService-->>-BotLogic: instance
        BotLogic->>+NotionService: await get_tasks_text()
        NotionService->>+NotionAPI: Fetch tasks
        NotionAPI-->>-NotionService: Task data
        NotionService-->>-BotLogic: tasks_json_str
        BotLogic->>BotLogic: Parse tasks_json_str
        alt Tasks found
            BotLogic->>DiscordUI: Send tasks message
            DiscordUI-->>User: Show tasks
        else No tasks or error
            BotLogic->>DiscordUI: Send fallback message
            DiscordUI-->>User: Show fallback message
        end
    end

    BotLogic->>SurveyManager: remove_survey(channel_id)
    Note over BotLogic: Survey Complete
```