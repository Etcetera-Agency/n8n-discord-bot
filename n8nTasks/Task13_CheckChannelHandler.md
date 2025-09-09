# Task 13: Check Channel Handler

## Goal
Implement `handle_check_channel` to report pending survey steps for the current channel. This command is triggered internally (`author` is `"system"`) before user interaction begins.

## Business Logic
- Use `channelId` to query the `n8n_survey_steps_missed` table for this week.
- Collect step names where `completed=false`.
- Return the list of unique pending steps. If none are found, the list is empty.
- Any database failure returns the generic error message.

### Input Variants
- **No pending steps** – all required steps are completed for the week.
- **Pending steps** – some steps exist with `completed=false`.
- **Database failure** – query raises an exception.

#### Example Payload
```json
{
  "command": "check_channel",
  "status": "ok",
  "message": "",
  "result": {},
  "userId": "YOUR_USER_ID",
  "channelId": "YOUR_CHANNEL_ID",
  "sessionId": "YOUR_CHANNEL_ID_YOUR_USER_ID",
  "author": "system",
  "channelName": "channel-name",
  "timestamp": 1678886400
}
```

### Output Variants
- Success: `{ "output": true, "steps": [] }`
- Error: `{ "output": "Спробуй трохи піздніше. Я тут пораюсь по хаті." }`

## Steps
1. Compute start of the current week (Monday 00:00 UTC).
2. **Read from Postgres** – `SELECT step_name, completed, updated FROM n8n_survey_steps_missed` filtering by `session_id` and `updated >= week_start`.
3. Collect step names with `completed=false` and remove duplicates.
4. Return `{ "output": true, "steps": pending_steps }` or the error message if the query fails.

## Pseudocode
```python
async def handle_check_channel(payload):
    try:
        repo = SurveyStepsDB(DATABASE_URL)
        start = start_of_week()
        records = await repo.fetch_week(payload["channelId"], start)
        steps = [r["step_name"] for r in records if not r["completed"]]
        return {"output": True, "steps": list(dict.fromkeys(steps))}
    except Exception:
        return {"output": "Спробуй трохи піздніше. Я тут пораюсь по хаті."}
```

## Tests
- Unit:
  - **No pending steps** – DB returns only `completed=true` rows.
  - **Pending steps** – DB returns at least one `completed=false` row.
  - **Database failure** – simulate exception and assert error message.
- End-to-end: dispatch `check_channel` and ensure the response contains the pending `steps` list.
- All tests must log inputs, steps, and outputs to a file for later review.
