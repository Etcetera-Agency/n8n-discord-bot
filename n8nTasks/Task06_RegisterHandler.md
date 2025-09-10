# Task 06: Register Handler

## Goal
Implement `handle_register` for the `!register` prefix command so the router can register a user without n8n.

## Business Logic
- Search the Team Directory in Notion for a page with the current `channelId`.
- If nothing is found, search by the desired display name to reuse an existing page.
- Each entry exposes `Name`, `Discord ID`, `Discord channel ID`, and `ToDo` properties.
- If a page exists for another user, respond that the channel is taken.
- If a page is found by name but lacks IDs, update it with the current `userId` and `channelId`.
- If still no page exists, create one with the provided display name and associate it with the channel and `userId`.

### Input Variants
- **New registration** – user issues `!register` with a display name.
- **Channel already taken** – channel is registered to someone else.
- **Generic failure** – any Notion error triggers the fallback message.

#### Example Payload
```json
{
  "command": "register",
  "status": "ok",
  "message": "!register User Name",
  "result": {
    "text": "User Name"
  },
  "userId": "YOUR_USER_ID",
  "channelId": "YOUR_CHANNEL_ID",
  "sessionId": "YOUR_CHANNEL_ID_YOUR_USER_ID",
  "author": "YourUsername#Discriminator",
  "channelName": "channel-name",
  "timestamp": 1678886400
}
```

### Output Variants
- Success: `{ "output": "Канал успішно зареєстровано на {property_name}" }`
- Channel taken: `{ "output": "Канал вже зареєстрований на когось іншого." }`
- Error: `{ "output": "Спробуй трохи піздніше. Я тут пораюсь по хаті." }`

## Steps
1. Parse the desired display name from `payload["result"]["text"]`.
2. **Read from Notion** – `POST /v1/databases/{TD_DB}/query` filtering by
   `"Discord channel ID" == payload.channelId`.
   Example response (trimmed from `responses`):
   ```json
   {
     "results": [
       {
         "id": "abc",
         "url": "https://www.notion.so/Roman-Lernichenko-b02bf04c43e4404ca4e21707ae8b61cc",
         "properties": {
           "Name": {"title": [{"plain_text": "Roman Lernichenko"}]},
           "Discord ID": {"rich_text": []},
           "Discord channel ID": {"rich_text": []},
           "ToDo": {
             "rich_text": [
               {"plain_text": "Todo - Roman Lernichenko", "href": "https://www.notion.so/11cc3573e5108104a0f1d579c3f9a648"},
               {"plain_text": " https://www.notion.so/11cc3573e5108104a0f1d579c3f9a648"}
             ]
           }
         }
       }
     ]
   }
   ```
3. If no page is found by channel ID, query `TD_DB` again filtering by
   `"Name" == name`. If a page exists, patch it with the new IDs; otherwise
   create one with:
   ```json
   {
     "parent": {"database_id": "{TD_DB}"},
     "properties": {
       "Name": {"title": [{"text": {"content": "User Name"}}]},
       "Discord ID": {"rich_text": [{"text": {"content": "YOUR_USER_ID"}}]},
       "Discord channel ID": {"rich_text": [{"text": {"content": "YOUR_CHANNEL_ID"}}]}
     }
   }
   ```
   Example success response: `{ "url": "https://www.notion.so/new-page" }`.
4. Return a confirmation or error message based on the outcome.

## Pseudocode
```python
async def handle_register(payload):
    name = payload["result"]["text"]
    try:
        page = await notion.find_channel(payload["channelId"])
        if page and page["discord_id"] != payload["userId"]:
            return {"output": "Канал вже зареєстрований на когось іншого."}
        if not page:
            page = await notion.find_by_name(name)
        if page:
            await notion.update_channel(page["id"], payload["userId"], payload["channelId"])
        else:
            await notion.create_channel(payload["channelId"], payload["userId"], name)
        return {"output": f"Канал успішно зареєстровано на {name}"}
    except Exception:
        return {"output": "Спробуй трохи піздніше. Я тут пораюсь по хаті."}
```

## Tests
- Unit:
  - **Channel free** – mock `notion.find_channel` to return `None` and ensure `create_channel` is called.
  - **Channel taken** – mock `notion.find_channel` to return `{"discord_id": "other"}` and verify handler returns the "taken" message.
  - **Notion error** – mock `create_channel` to raise an exception and assert the fallback message.
  - Example Notion search response when channel free: `null`.
  - Example Notion search response when channel occupied:
    ```json
    {
      "id": "abc",
      "url": "https://www.notion.so/Roman-Lernichenko-b02bf04c43e4404ca4e21707ae8b61cc",
      "name": "Roman Lernichenko",
      "discord_id": "321",
      "channel_id": "1234567890",
      "to_do": "https://www.notion.so/11cc3573e5108104a0f1d579c3f9a648"
    }
    ```
- End-to-end: send `!register` and assert the bot responds with the registration confirmation template.
- All tests must log inputs, steps, and outputs to a file for later review.