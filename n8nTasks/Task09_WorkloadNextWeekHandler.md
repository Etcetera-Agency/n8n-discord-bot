# Task 09: Workload Next Week Handler

## Goal
Implement `handle_workload_nextweek` so planned hours for next week are saved without n8n.

## Business Logic
- Extract `hours` from the payload, allowing `0`.
- Retrieve the user's workload page URL and stats from Notion.
- Write to the `"Next week plan"` field and mark the `workload_nextweek` survey step as completed.
- On any Notion failure return the generic error message.
- when write to n8n_survey_steps_missed session_id is always channel_id only.


### Input Variants
- **Standalone command** `workload_nextweek` with numeric `result.value` (0 allowed).
- **Survey step** with `result.stepName` == `workload_nextweek`.
- **Generic failure** if Notion tools fail.

#### Example Payload
```json
{
  "command": "workload_nextweek",
  "status": "ok",
  "message": "",
  "result": {
    "value": 15
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
- Success: `{ "output": "Записав! \nЗаплановане навантаження на наступний тиждень: {hours} год." }`
- Error: `{ "output": "Спробуй трохи піздніше. Я тут пораюсь по хаті." }`

## Steps
1. Extract hours from `payload["result"]["value"]`.
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
           "Next week plan": {"number": 0}
         }
       }
     ]
   }
   ```
3. Set `day_field` to "Next week plan".
4. **Write to Notion** – `PATCH /v1/pages/424fc389-c898-48d1-91d6-68dd36585fd7` with:
   ```json
   {
     "properties": {
       "Next week plan": {"number": 15}
     }
   }
   ```
   Example success response: `{ "properties": {"Next week plan": {"number": 15}} }`.
5. Mark the survey step complete and return a localized confirmation or error message.

## Pseudocode
```python
async def handle_workload_nextweek(payload):
    try:
        hours = int(payload["result"]["value"])  # 0 is valid
        page = await notion.get_workload_page(payload["author"])
        await notion.write_plan_hours(page["url"], hours, "Next week plan")
        await survey.mark_step(payload["userId"], "workload_nextweek")
        return {"output": templates.workload_nextweek(hours)}
    except Exception:
        return {"output": "Спробуй трохи піздніше. Я тут пораюсь по хаті."}
```

## Tests
- Unit:
  - **Valid write** – mock `get_workload_page` to return `{ "url": "https://notion.so/page" }` and ensure `write_plan_hours`
    is called with `"Next week plan"` and provided hours.
  - **Notion failure** – mock `write_plan_hours` to raise an exception and assert the error message.
- End-to-end: simulate `/workload_nextweek` and verify the confirmation message.
- All tests must log inputs, steps, and outputs to a file for later review.
