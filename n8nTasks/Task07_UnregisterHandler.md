# Task 07: Unregister Handler

## Goal
Implement `handle_unregister` for the `!unregister` prefix command so the router can remove a user without n8n.

## Business Logic
- Look up the channel in the Team Directory using `channelId`.
- Each entry exposes `Name`, `Discord ID`, `Discord channel ID`, and `ToDo` properties.
- If no page is found, respond that the channel is not registered.
- If a page exists, clear its `Discord ID` and `Discord channel ID` fields so the entry remains in the Team Directory.
- Any failure when accessing Notion produces a fallback error.

### Input Variants
- **Channel registered** – user issues `!unregister` from a registered channel.
- **Channel absent** – command comes from a channel not registered to anyone.
- **Generic failure** – any Notion error triggers the fallback message.

#### Example Payload
```json
{
  "command": "unregister",
  "status": "ok",
  "message": "!unregister",
  "result": {},
  "userId": "YOUR_USER_ID",
  "channelId": "YOUR_CHANNEL_ID",
  "sessionId": "YOUR_CHANNEL_ID_YOUR_USER_ID",
  "author": "YourUsername#Discriminator",
  "channelName": "channel-name",
  "timestamp": 1678886400
}
```

### Output Variants
- Success: `{ "output": "Готово. Тепер цей канал не зареєстрований ні на кого." }`
- Channel not found: `{ "output": "Вибачте, але цей канал не зареєстрований ні на кого. Тому не можу зняти його з реєстрації" }`
- Error: `{ "output": "Спробуй трохи піздніше. Я тут пораюсь по хаті." }`

## Steps
1. **Read from Notion** – `POST /v1/databases/{TD_DB}/query` filtering by
   `"Discord channel ID" == payload.channelId`.
   Sample response when the page exists (from `responses`):
   ```json
   {
     "results": [
       {
         "id": "page123",
         "url": "https://www.notion.so/Roman-Lernichenko-b02bf04c43e4404ca4e21707ae8b61cc",
         "properties": {
           "Name": {"title": [{"plain_text": "Roman Lernichenko"}]},
           "Discord ID": {"rich_text": []},
           "Discord channel ID": {"rich_text": []},
           "ToDo": {"rich_text": [{"plain_text": "Todo - Roman Lernichenko"}]}
         }
       }
     ]
   }
   ```
2. If no results, return the "not registered" message.
3. **Write to Notion** – clear identifying fields with `PATCH /v1/pages/page123`:
   ```json
   {
     "properties": {
       "Discord ID": {"rich_text": []},
       "Discord channel ID": {"rich_text": []}
     }
   }
   ```
   Example success response: `{ "properties": {"Discord ID": {"rich_text": []}} }`.
4. Return a confirmation or error message.

## Pseudocode
```python
async def handle_unregister(payload):
    try:
        page = await notion.find_channel(payload["channelId"])
        if not page:
            return {"output": "Вибачте, але цей канал не зареєстрований ні на кого. Тому не можу зняти його з реєстрації"}
        await notion.clear_channel(page["id"])
        return {"output": "Готово. Тепер цей канал не зареєстрований ні на кого."}
    except Exception:
        return {"output": "Спробуй трохи піздніше. Я тут пораюсь по хаті."}
```

## Tests
- Unit:
  - **Channel exists** – mock `notion.find_channel` to return a page and ensure `clear_channel` is called.
  - **Channel missing** – mock `notion.find_channel` to return `None` and verify the "not registered" message.
  - **Notion error** – mock `clear_channel` to raise an exception and assert fallback message.
  - Example Notion lookup when channel missing: `null`.
  - Example Notion lookup when channel exists:
    ```json
    {
      "id": "page123",
      "url": "https://www.notion.so/Roman-Lernichenko-b02bf04c43e4404ca4e21707ae8b61cc",
      "name": "Roman Lernichenko",
      "discord_id": "321",
      "channel_id": "1234567890",
      "to_do": "https://www.notion.so/11cc3573e5108104a0f1d579c3f9a648"
    }
    ```
- End-to-end: send `!unregister` and verify the bot confirms the removal.
- All tests must log inputs, steps, and outputs to a file for later review.