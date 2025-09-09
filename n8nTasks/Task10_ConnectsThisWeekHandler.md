# Task 10: Connects This Week Handler

## Goal
Implement `handle_connects_thisweek` so the router records remaining Upwork connects for the week.

## Business Logic
- Pull the numeric connects value from the payload and mark the `connects_thisweek` survey step complete.
- Send the value to the connects database with an HTTP `POST` request to `https://tech2.etcetera.kiev.ua/set-db-connects` using body `{ "name": <user>, "connects": <count> }`.
- If a profile stats page exists, write the connects value to it, ignoring failures.
- Any failure in these operations returns the generic error message.

### Input Variants
- **Standalone command** `connects_thisweek` with numeric `result.connects`.
- **Survey step** with `result.stepName` == `connects_thisweek`.
- **Generic failure** if database writes fail.

#### Example Payload
```json
{
  "command": "connects_thisweek",
  "status": "ok",
  "message": "",
  "result": {
    "connects": 80
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
- Success: `{ "output": "Записав! Upwork connects: залишилось {connects} на цьому тиждні." }`
- Error: `{ "output": "Спробуй трохи піздніше. Я тут пораюсь по хаті." }`

## Steps
1. Extract connects count from `payload["result"]["connects"]`.
2. Update survey status and `POST` the count to the connects database.
3. **Read from Notion** – `POST /v1/databases/{PROFILE_DB}/query` with
   `"Name" == payload.author`. Example page response (from `responses`):
   ```json
   {
     "results": [
       {
         "id": "1b2c3573-e510-805a-9206-d827a66e7ae6",
         "url": "https://www.notion.so/Alex-Shibisty-1b2c3573e510805a9206d827a66e7ae6",
         "properties": {
           "Connects": {"number": null}
         }
       }
     ]
   }
   ```
4. **Write to Notion** – if a page exists, `PATCH /v1/pages/1b2c3573-e510-805a-9206-d827a66e7ae6` with:
   ```json
   {
     "properties": {
       "Connects": {"number": 80}
     }
   }
   ```
   Example success response: `{ "properties": {"Connects": {"number": 80}} }`.
5. Return a localized confirmation or error message.

## Pseudocode
```python
async def handle_connects_thisweek(payload):
    try:
        connects = int(payload["result"]["connects"])
        await survey.mark_step(payload["userId"], "connects_thisweek")
        await http.post(
            "https://tech2.etcetera.kiev.ua/set-db-connects",
            json={"name": payload["author"], "connects": connects},
        )
        stats = await notion.get_profile_stats(payload["author"])
        if stats:
            try:
                await notion.write_profile_stats(stats["url"], connects)
            except Exception:
                pass  # ignore profile write errors
        return {"output": f"Записав! Upwork connects: залишилось {connects} на цьому тиждні."}
    except Exception:
        return {"output": "Спробуй трохи піздніше. Я тут пораюсь по хаті."}
```

## Tests
- Unit:
  - **Profile exists** – mock `get_profile_stats` to return `{ "url": "https://notion.so/etcetera/" }` and ensure `write_profile_stats` is called.
  - **No profile** – mock `get_profile_stats` to return `[]` and verify no write occurs.
  - **Database error** – mock the HTTP `POST` to raise and assert the error message.
  - Example connects DB response:
    ```json
    {"status": "ok"}
    ```
  - Example Notion profile response:
    ```json
    {"url": "https://notion.so/etcetera/"}
    ```
- End-to-end: simulate `/connects_thisweek` and verify the confirmation message.
- All tests must log inputs, steps, and outputs to a file for later review.