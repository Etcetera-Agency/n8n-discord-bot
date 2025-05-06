# Overall Refactoring Plan: Standardized Survey Flow (Adjusted)

This plan aims to refactor the Discord bot's survey flow. It will implement a standardized per-step interaction pattern, integrate Notion task fetching at the end, remove excessive logging, and document the process, all while preserving existing slash command functionality.

**Important Considerations:**

*   The survey is channel-bound, not user-bound. Interaction handling must use the channel ID.
*   Payloads sent to n8n must maintain their existing structure and content, except for the specific step data or final completion data.
*   Existing slash command functionality must remain unaffected.
*   Message deletion and reaction logic will be handled as described in the plan.
*   Robust error handling for the Notion API call is crucial.
*   Excessive logging will be removed or adjusted.
*   Crucially, the refactoring will maintain that only specific steps (like 'connects_this week') use modals for input, while other steps may use alternative interaction methods (e.g., views). The standardized button -> modal flow applies only to steps designed for modal input.
*   The survey is initiated by clicking the "Гайда" button on a persistent greeting message ("Готовий почати робочий день?") in the channel. This button should be clickable by any user at any time to start a new survey session if one is not already active for that channel.

**Goals:**

1.  Implement the standardized per-step interaction flow: Initial message with "Ввести" button -> Button disabled & reaction added on click -> Determine interaction type (Modal or View) -> Present Modal or View -> Handle input (Modal Submission or View Interaction) -> Input saved & per-step webhook sent -> Initial message updated, reaction/button/view removed -> Next step or completion.
2.  Implement the final survey completion logic: Verify/Adjust the `finish_survey` function to gather results and send the final webhook (`status: "end"`). Handle the final webhook response, sending the output message. Implement Notion task fetching using the provided URL, including error handling. Display fetched tasks or a fallback message. Clean up the survey state by removing it from the `SurveyManager`. Update relevant configuration and strings.
3.  Remove excessive logging throughout the survey and related code.
4.  Ensure existing slash command functionality remains unchanged.
5.  (Already completed) Create new markdown files in the `tasks` directory detailing the refactoring steps.

**Primary Affected Files:**

*   `discord_bot/commands/survey.py`: Core logic for survey start, step handling, interaction responses, modal handling, and completion.
*   `services/survey.py`: `SurveyFlow` class for state management.
*   `services/webhook.py`: For sending webhooks and handling responses.
*   `services/notion_todos.py`: For fetching Notion tasks.
*   `discord_bot/views/`: Existing views might need review, new modals will be defined or modified.
*   `config/logger.py`: Ensure correct logging setup is used.
*   `config/strings.py` / `config/constants.py`: For messages, button labels, and step definitions.

**Detailed Steps (Broken into Individual Tasks):**

This refactoring will be broken down into the following individual tasks:

**Task 1: Refactor Survey Step Interaction**
*   Ensure the initial greeting message with the "Гайда" button is present and interactive in the channel. Implement the callback for the "Гайда" button to check for an existing survey session for the channel and, if none exists, initiate a new survey flow by calling the appropriate logic (e.g., checking channel registration with n8n and creating a new SurveyFlow instance).
*   Analyze current survey code and adjust for channel-bound interactions.
*   Refine `SurveyFlow` and `SurveyManager` to use `channel_id` as the key and store message IDs.
*   Modify `ask_dynamic_step` to send the initial message containing the question and a "Ввести" button for *all* steps.
*   Implement the "Ввести" button callback to:
    *   Retrieve the `SurveyFlow` object using the `interaction.channel.id`.
    *   Disable the button on the initial message and add a "⏳" reaction.
    *   Determine the required interaction type (Modal or View) based on the current step definition.
    *   If Modal is required (e.g., 'connects_this week'), show the appropriate modal.
    *   If a View is required, send or update the message with the appropriate view containing further buttons.
*   Refine modal submission handling (`on_submit` / `handle_modal_submit`) to process input from modals.
*   Refine view interaction handling to process input from views.
*   After processing input (from either modal or view): send a per-step webhook, update the initial message (remove reaction/button/view as appropriate) with n8n output, and advance the survey.
*   Update relevant configuration and constants.

**Task 2: Implement Survey Finalization and Notion Fetching**
*   Verify/Adjust the `finish_survey` function to send the final webhook (`status: "end"`).
*   Handle the final webhook response, sending the output message.
*   Verify/Adjust Notion task fetching using the provided URL, including error handling.
*   Display fetched tasks or a fallback message.
*   Clean up the survey state by removing it from the `SurveyManager`.
*   Update relevant configuration and strings.

**Task 3: Clean Up Excessive Survey Logging**
*   Review logging statements in survey-related files.
*   Identify and remove or adjust excessive or redundant logs.
*   Ensure critical errors are still logged appropriately.
*   Verify the logging setup.

**Flow Diagram (Updated Survey Step):**

```mermaid
sequenceDiagram
    participant User
    participant BotLogic as "Bot Logic (survey.py)"
    participant DiscordUI as "Discord UI (Messages, Modals, Views)"
    participant SurveyManager as "SurveyManager (services/survey.py)"
    participant WebhookService as "WebhookService (services/webhook.py)"
    participant N8N as "n8n Webhook"
    participant NotionService as "Notion_todos (services/notion_todos.py)"
    participant NotionAPI as "Notion API"

    %% Initial Survey Trigger
    User->>DiscordUI: Sees persistent greeting message with "Гайда" button
    User->>DiscordUI: Clicks "Гайда" button
    DiscordUI->>BotLogic: Interaction received (Гайда button click)
    BotLogic->>SurveyManager: get_survey(channel_id)
    alt Survey Exists for Channel
        SurveyManager-->>BotLogic: Existing SurveyFlow
        BotLogic->>DiscordUI: Send message: "Survey already in progress."
        DiscordUI-->>User: Show message
        return
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

        %% User Clicks "Ввести" Button
        User->>DiscordUI: Clicks "Ввести" Button
        DiscordUI->>BotLogic: Interaction received ("Ввести" button click)
        BotLogic->>DiscordUI: Disable Button (edit message)
        BotLogic->>DiscordUI: Add ⏳ reaction (edit message)
        BotLogic->>BotLogic: Determine interaction type for step

        alt Step requires Modal (e.g., connects_this week)
            BotLogic->>DiscordUI: Show Step Modal (send_modal)
            DiscordUI-->>User: Show Modal

            %% User Submits Modal
            User->>DiscordUI: Submits Modal (input)
            DiscordUI->>BotLogic: Interaction received (modal submit)
            BotLogic->>BotLogic: Validate & Store Input (survey.add_result)
        else Step uses other interaction (e.g., View)
            BotLogic->>DiscordUI: Send/Update message with View
            DiscordUI-->>User: Show View

            %% User Interacts with View
            User->>DiscordUI: Interacts with View
            DiscordUI->>BotLogic: Interaction received (view interaction)
            BotLogic->>BotLogic: Process View Input & Store Result (survey.add_result)
        end

        %% Common Logic After Input
        BotLogic->>+WebhookService: send_webhook(step_payload)
        WebhookService->>+N8N: POST /webhook (status: step, stepName, result, user_id, channel_id, session_id)
        N8N-->>-WebhookService: Response {output: "...", survey: "continue"}
        WebhookService-->>-BotLogic: return success, response

        alt Step required Modal
            BotLogic->>DiscordUI: Remove ⏳ reaction (edit message)
            BotLogic->>DiscordUI: Remove Button (edit message)
            BotLogic->>DiscordUI: Delete Modal message (if applicable)
        else Step used other interaction
            BotLogic->>DiscordUI: Remove ⏳ reaction (edit message) %% Still remove reaction added on button click
            BotLogic->>DiscordUI: Update/Remove View (edit message)
        end
        BotLogic->>DiscordUI: Update initial message content (edit message)

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