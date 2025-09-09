# Task 13: Check Channel Handler

## Goal
Implement `handle_check_channel` to report pending survey steps for the current channel. The survey command sends a system webhook with this payload before any user interaction begins.

## Business Logic
- Select rows from `n8n_survey_steps_missed` where `session_id` equals `channelId`.
- In memory:
  1. Compute start of the week (Monday 00:00, Europe/Kyiv) and today's name.
  2. Start with today's scheduled steps and drop any that have a record marked `completed=true` and `updated` today.
  3. Add any rows where `completed=false` and `updated` falls within the current week.
  4. Return the unique set of step names.
- On database failure, return `{ "output": false, "message": "Спробуй трохи піздніше. Я тут пораюсь по хаті." }`.

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
- Error: `{ "output": false, "message": "Спробуй трохи піздніше. Я тут пораюсь по хаті." }`

## Steps
1. Select `step_name`, `completed`, and `updated` from `n8n_survey_steps_missed` for the given `session_id`.
2. Compute the start of the current week and process records as described above to build the pending steps list.
3. Return `{ "output": true, "steps": pending_steps }` or `{ "output": false, "message": ... }` if the query fails.
4. Close the database connection in a `finally` block if it was created inside the handler.

## Pseudocode
```python
async def handle_check_channel(payload):
    db = SurveyStepsDB(DATABASE_URL)
    try:
        now = now_in_kyiv()
        start = start_of_week(now)
        records = await db.fetch_week(payload["channelId"], start)
        steps = [r["step_name"] for r in records if not r["completed"]]
        return {"output": True, "steps": list(dict.fromkeys(steps))}
    except Exception:
        return {"output": False, "message": "Спробуй трохи піздніше. Я тут пораюсь по хаті."}
    finally:
        await db.close()
```

## Tests
- Unit:
  - **No pending steps** – DB returns only `completed=true` rows.
  - **Pending steps** – DB returns at least one `completed=false` row.
  - **Database failure** – simulate exception and assert error message.
- End-to-end: dispatch `check_channel` and ensure the response contains the pending `steps` list.
- All tests must log inputs, steps, and outputs to a file for later review.
