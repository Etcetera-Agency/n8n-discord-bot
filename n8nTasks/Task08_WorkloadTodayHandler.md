# Task 08: Workload Today Handler

## Goal
Implement `handle_workload_today` so the router can record today's workload directly in the Notion database.

## Business Logic
- Extract `hours` from the payload and treat `0` as a valid value.
- Fetch the user's workload page URL and stats from Notion using their name,
  retrieving both current `Fact` and weekly `Capacity` values for the
  response template.
- Determine the correct `day_field` (e.g., `Mon Plan`) for today's date.
- Write the hours to Notion and mark the `workload_today` survey step as completed.
- On any Notion failure return the generic error message.

### Input Variants
- **Standalone command** `workload_today` with `result.value` as number (0 allowed).
- **Survey step** `survey` with `result.stepName` == `workload_today` and `result.value` as number.
- **Generic failure** if Notion tools fail.

#### Example Payload
```json
{
  "command": "workload_today",
  "status": "ok",
  "message": "",
  "result": {
    "value": 20
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
- Success: `{ "output": "Записав! \nЗаплановане навантаження у {день тиждня}: {hours} год. \nВ щоденнику з понеділка до {день тиждня}: {user.property_fact} год.\nКапасіті на цей тиждень: {user.property_capasity} год." }`
- Error: `{ "output": "Спробуй трохи піздніше. Я тут пораюсь по хаті." }`

## Steps
1. Extract planned hours from `payload["result"]["value"]`.
2. **Read from Notion** – `POST /v1/databases/{WORKLOAD_DB}/query` with
   `"Name" == payload.author`.
   Example response (from `responses`):
   ```json
   {
     "results": [
       {
        "id": "424fc389-c898-48d1-91d6-68dd36585fd7",
        "url": "https://www.notion.so/...",
         "properties": {
           "Capacity": {"number": 16},
           "Mon Fact": {"number": 1},
           "Mon Plan": {"number": 0}
         }
       }
     ]
   }
   ```
3. Determine the correct `day_field` based on today's weekday.
4. **Write to Notion** – `PATCH /v1/pages/424fc389-c898-48d1-91d6-68dd36585fd7` with:
   ```json
   {
     "properties": {
       "Mon Plan": {"number": 20}
     }
   }
   ```
   Example success response: `{ "properties": {"Mon Plan": {"number": 20}} }`.
5. Mark the survey step complete and return a localized confirmation or error message.

## Pseudocode
```python
async def handle_workload_today(payload):
    try:
        hours = int(payload["result"]["value"])  # 0 is valid
        page = await notion.get_workload_page(payload["author"])
        day_field = compute_today_plan_field()
        await notion.write_plan_hours(page["url"], hours, day_field)
        await survey.mark_step(payload["userId"], "workload_today")
        return {
            "output": templates.workload_today(
                day_field,
                hours,
                page["properties"]["Fact"],
                page["properties"]["Capacity"],
            )
        }
    except Exception:
        return {"output": "Спробуй трохи піздніше. Я тут пораюсь по хаті."}
```

## Tests
- Unit:
  - **Valid write** – mock `get_workload_page` to return a page like:
    ```json
    {"url": "https://notion.so/page", "properties": {"Fact": 10, "Capacity": 40}}
    ```
    Ensure `write_plan_hours` is called with the computed `day_field` and provided hours.
  - **Notion failure** – mock `write_plan_hours` to raise an exception and assert the error message.
- End-to-end: simulate `/workload_today` and assert the confirmation message matches the template.
- All tests must log inputs, steps, and outputs to a file for later review.
