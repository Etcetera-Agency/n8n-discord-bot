# Task: Add Notion ToDo Fetching at Survey End

## 1. Goal

Modify the bot's end-of-survey process. When n8n responds to the `status: "end"` webhook, it will include an `output` message and a Notion `url`. The bot will first send the `output` message, then use the `url` with `services/Notion_todos.py` to fetch unchecked ToDo tasks created within the last 14 days from the specified Notion page. If tasks are found, they will be sent as a separate message. If fetching fails, a standard "Дякую. /nЧудового дня!" message will be sent instead. Documentation will be updated.

## 2. Code Changes

*   **`discord_bot/commands/survey.py` (inside `async def finish_survey`):**
    *   Locate the section after `success, response = await webhook_service.send_webhook_with_retry(...)`.
    *   **Replace** the current `await channel.send(str(response))` block with logic to:
        *   Check if `success` is `True` and `response` is a dictionary.
        *   Send `response.get("output")` to the `channel` if it exists.
        *   If `notion_url := response.get("url")` exists:
            *   Add imports: `import json` and `from services.notion_todos import Notion_todos`.
            *   Wrap in `try...except (ValueError, ConnectionError, json.JSONDecodeError, Exception) as e:`:
                *   Instantiate: `notion_service = Notion_todos(todo_url=notion_url, days=14)`.
                *   Fetch: `tasks_json_str = await notion_service.get_tasks_text()`.
                *   Parse: `tasks_data = json.loads(tasks_json_str)`.
                *   If `tasks_data.get("tasks_found")`: send `tasks_data.get("text")` as a new message.
                *   In `except` block: Log error details (`logger.error(f"Failed to fetch Notion tasks from URL {notion_url}: {e}", exc_info=True)`) and send fallback message `await channel.send("Дякую. /nЧудового дня!")`.
            *   Else (no `notion_url`): Log debug message.
        *   Else (webhook failed): Handle error (e.g., `raise Exception(...)`).
*   **`services/Notion_todos.py`:**
    *   Modify `get_tasks_text` and `_extract_todos` to be `async def`.
    *   Ensure `notion-client` calls are awaited (or handle synchronous nature appropriately - *Note: Further investigation might be needed during implementation if the client library is strictly synchronous*).

## 3. Documentation Changes

*   **`README.md`:**
    *   Update the "n8n Responses to Bot" section, specifically the example for survey completion (`status: "end"`). Add the `"url": "YOUR_NOTION_PAGE_URL"` field to the example JSON response.
    *   Add a paragraph explaining that if the `url` field is provided, the bot will attempt to fetch ToDo tasks from the last 14 days using `services/Notion_todos.py` and send them as a final message.
    *   Mention that the `NOTION_TOKEN` environment variable must be set for this feature to function.

## 4. Flow Diagram (finish_survey)

```mermaid
sequenceDiagram
    participant Bot as "Bot (finish_survey)"
    participant WebhookService as "WebhookService"
    participant N8N as "n8n"
    participant Discord as "Discord Channel"
    participant NotionService as "Notion_todos"
    participant NotionAPI as "Notion API"
    participant SurveyManager as "SurveyManager"
    participant Logger

    Bot->>+WebhookService: send_webhook_with_retry(payload: {status: 'end', ...})
    WebhookService->>+N8N: POST /webhook {status: 'end', ...}
    N8N-->>-WebhookService: Response {output: "...", survey: "end", url: "..."}
    WebhookService-->>-Bot: return success=True, response={...}

    alt Webhook Success and Response Valid
        Bot->>Bot: Parse response
        opt response["output"] exists
            Bot->>Discord: Send message (response["output"])
        end
        opt response["url"] exists
            Bot->>Bot: notion_url = response["url"]
            try
                Bot->>+NotionService: Instantiate Notion_todos(url=notion_url, days=14)
                NotionService-->>-Bot: instance
                Bot->>+NotionService: await get_tasks_text()
                NotionService->>+NotionAPI: Retrieve/List Blocks
                NotionAPI-->>-NotionService: Block Data
                NotionService->>NotionService: Process Todos (last 14 days)
                NotionService-->>-Bot: tasks_json_str
                Bot->>Bot: Parse JSON tasks_data
                alt tasks_data["tasks_found"] is True
                    Bot->>Discord: Send message (tasks_data["text"])
                end
            catch Error (ValueError, ConnectionError, JSONDecodeError, Exception)
                Bot->>Logger: Log error details (URL, exception)
                Bot->>Discord: Send message ("Дякую. /nЧудового дня!")
            end
        else No Notion URL
             Bot->>Logger: Log debug message (No URL)
        end
    else Webhook Failed or Bad Response
        Bot->>Bot: Handle webhook error (e.g., raise Exception)
        Bot->>Logger: Log error
    end

    Bot->>SurveyManager: remove_survey(user_id) # In finally block