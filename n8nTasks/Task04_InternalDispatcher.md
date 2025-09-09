# Task 04: Internal webhook dispatcher

## Goal
Replace the external n8n webhook call with an internal router that routes payloads to Python handlers, distinguishing between standalone commands, mention queries, and survey steps.

## Steps
1. Use the Notion connector to look up the channel in the Team Directory (`payload["channelId"]`) and enrich the payload with the user's name, Discord ID, and to-do URL. Example lookup result:
   ```json
   {
     "id": "PAGE_ID",
     "url": "https://www.notion.so/Roman-Lernichenko-b02bf04c43e4404ca4e21707ae8b61cc",
     "name": "Roman Lernichenko",
     "discord_id": "321",
     "channel_id": "1234567890",
     "to_do": "https://www.notion.so/11cc3573e5108104a0f1d579c3f9a648"
   }
   ```
2. Create a `router` module with a registry mapping command names to handler coroutines (e.g., `register`, `mention`). Survey steps reuse these same handlers.
3. Modify `services/webhook.py` so `send_webhook` builds the payload and forwards it to `router.dispatch` instead of performing an HTTP request.
4. Inside `router.dispatch`, determine whether the payload is part of an active survey:
   - If `payload["command"] == "survey"` or `survey_manager.is_active(payload["userId"])`, treat it as a survey step and use `payload["result"]["stepName"]` to select the handler.
   - If `payload["type"] == "mention"`, route directly to the mention handler.
   - Otherwise, treat it as a standalone command and use `payload["command"]`.
5. After invoking the handler, wrap its result:
   - For survey steps, include survey metadata (`status`, `next_step`) along with the handler's output. Append the `user.to_do` URL retrieved in step 1 when the survey ends.
   - For standalone commands and mentions, return only the handler's output.
6. Implement a `handle_mention` helper that returns the placeholder message defined in `n8n-workflow.json`.
7. Ensure the dispatcher returns the same response structure currently produced by n8n.

### Input Variants
- **Standalone command** – `payload["command"]` matches a handler name such as `register` or `workload_today`.
- **Survey step** – `payload["command"] == "survey"` or the survey manager reports an active session; `payload["result"]["stepName"]` selects the handler.
- **Mention** – `payload["type"] == "mention"` and `payload["message"]` holds free‑form text.

### Output Variants
- **Non‑survey commands and mentions** must return the JSON shape:

  ```json
  {
    "output": "string"
  }
  ```

- **Survey steps** must return:

  ```json
  {
    "output": "string", // The message content to potentially display to the user. Cannot be null, if some error contains error message 
    "survey": "string"   // Describes the survey context: "continue", "end", "cancel" got from output
  }
  ```

- **Survey steps when `status` is `end`** add a URL to the user's to‑do:

  ```json
  {
    "output": "string", // The message content to potentially display to the user. Cannot be null. if some error contains error message 
    "survey": "string"   // Describes the survey context: "continue", "end", "cancel"
    "url": {{ $("Set").item.json.user.to_do }}  .
  }
  ```

### Mention Business Logic
- Respond with a static message instructing the user to use slash commands: "Я ще не вмію вільно розмовляти. Використовуй слеш команди <@{userId}>. Почни із /".

#### Example Payload
```json
{
  "type": "mention",
  "status": "ok",
  "message": "@Etcetera-Bot What is the weather like today?",
  "result": {},
  "userId": "YOUR_USER_ID",
  "channelId": "YOUR_CHANNEL_ID",
  "sessionId": "YOUR_CHANNEL_ID_YOUR_USER_ID",
  "author": "YourUsername#Discriminator",
  "channelName": "channel-name",
  "timestamp": 1678886400
}
```

#### Response Template
```json
{
  "output": "Я ще не вмію вільно розмовляти. Використовуй слеш команди <@YOUR_USER_ID>. Почни із /"
}
```

## Pseudocode
```python
# router.py
HANDLERS = {
    "mention": handle_mention,
    "register": handle_register,
    "unregister": handle_unregister,
    # ...other handlers
}

async def dispatch(payload: dict) -> dict:
    # fetch user info for channel and enrich payload
    user = await notion.lookup_channel(payload["channelId"])
    payload["userId"] = user["discord_id"]
    payload["author"] = user["name"]
    todo_url = user["to_do"]

    if payload.get("command") == "survey" or survey_manager.is_active(payload["userId"]):
        step = payload["result"]["stepName"]
        try:
            output = await HANDLERS[step](payload)
        except Exception as err:
            return {"output": str(err), "survey": "cancel"}
        state = survey_manager.advance(payload["userId"], step)
        response = {"output": output, "survey": state.flag}
        if state.flag == "end":
            response["url"] = todo_url
        return response
    if payload["command"] == "mention":
        output = await HANDLERS["mention"](payload)
        return {"output": output}
    try:
        handler = HANDLERS[payload["command"]]
        output = await handler(payload)
        return {"output": output}
    except Exception:
        return {"output": "Спробуй трохи піздніше. Я тут пораюсь по хаті."}
```

## Tests
- Unit: mock mention, command and survey payloads to verify `dispatch` selects handlers correctly and wraps outputs appropriately, including the `url` field on survey completion.
- End-to-end: simulate a mention, a standalone command, and a full survey flow to confirm responses match samples in `responses` and no outbound HTTP request occurs.
- All tests must log inputs, steps, and outputs to a file for later review.
