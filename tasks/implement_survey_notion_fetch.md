# Task: Implement Survey Finalization and Notion Fetching

This task focuses on implementing the final steps of the survey flow, which occur after the last step's input has been processed. This includes sending a final webhook to n8n, handling the response, and fetching/displaying Notion tasks if a URL is provided.

**Important Considerations:**

*   The final webhook payload structure to n8n must match the existing implementation's expectation for survey completion.
*   Error handling for the Notion API call is crucial to provide graceful fallback messages to the user.
*   The survey should be removed from the `SurveyManager` upon successful completion or error in the finalization step.

**Affected Files:**

*   `discord_bot/commands/survey.py` (`finish_survey` function)
*   `services/webhook.py`
*   `services/notion_todos.py`
*   `services/survey.py` (`SurveyManager`)
*   `config/strings.py`

**Steps:**

1.  **Refine `finish_survey` Function:**
    *   Locate or create the `finish_survey` function in `discord_bot/commands/survey.py`.
    *   This function should be called after the last step's modal submission is processed and its per-step webhook is handled.
    *   Gather all collected results from the channel's `SurveyFlow` object.
    *   Construct the final webhook payload to n8n. This payload should include `command: "survey"`, `status: "end"`, the `channel_id`, `user_id` (from the last interaction), `session_id`, and the complete `result` dictionary containing all answers.
    *   Call `services.webhook.send_webhook` (or the appropriate method) to send this final payload to n8n.
2.  **Handle Final Webhook Response:**
    *   Process the response received from the final n8n webhook. The response is expected to contain a final `output` message and potentially a `url` for Notion tasks.
    *   Send the `output` message from the n8n response to the survey channel.
3.  **Implement Notion Task Fetching:**
    *   Check if a `url` field is present in the n8n webhook response.
    *   If a `url` exists:
        *   Add necessary imports for `services.notion_todos` and exception handling (e.g., `try...except`).
        *   Instantiate `services.notion_todos.Notion_todos` with the provided `url` and a fixed date range (e.g., 14 days).
        *   Call the appropriate asynchronous method (e.g., `await notion_service.get_tasks_text()`) to fetch tasks from Notion.
        *   Handle potential exceptions during the Notion API call (e.g., `ValueError`, `ConnectionError`, `json.JSONDecodeError`, or a general `Exception`). Log the error details.
        *   If tasks are successfully fetched and the response indicates tasks were found, format the task data and send it as a separate message to the survey channel.
        *   If fetching fails or no tasks are found, send the fallback "Дякую. \nЧудового дня!" message (or a similar localized completion message).
4.  **Clean up Survey State:**
    *   After sending the final messages (either tasks or the fallback), call `services.survey.SurveyManager.remove_survey(channel_id)` to remove the completed survey session.
5.  **Update Configuration/Strings:**
    *   Add or update any necessary strings in `config/strings.py` for the final completion message, fallback message, or any error messages related to Notion fetching.