# Task 12: Vacation Handler

## Goal
Implement `handle_vacation` so users can log vacations directly through the bot.

## Business Logic
- Extract `start_date` and `end_date` from the payload.
- Create a calendar event with:
  - `summary`: `"Vacation: {user.name}"`
  - `start`: `"{start_date} 00:00:00"`
  - `end`:   `"{end_date} 23:59:59"`
  and mark `vacation` as completed.
- Respond with a summary of the scheduled vacation, formatting dates as
  `WEEKDAY DD MMMM` using a date utility.
- Any calendar failure returns the generic error message.

### Input Variants
- **Standalone command** `vacation` with `result.start_date` and `result.end_date`.
- **Survey step** with `result.stepName` == `vacation`.
- **Generic failure** if calendar write fails.

#### Example Payload
```json
{
  "command": "vacation",
  "status": "ok",
  "message": "",
  "result": {
    "start_date": "YYYY-MM-DD",
    "end_date": "YYYY-MM-DD"
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
- Success: `{ "output": "Записав! Відпустка: {start WEEKDAY DD MMMM}—{end WEEKDAY DD MMMM}." }`
- Error: `{ "output": "Спробуй трохи піздніше. Я тут пораюсь по хаті." }`

## Steps
1. Extract start and end dates from `payload["result"]`.
2. Call `calendar.create_event("Vacation: {user.name}", f"{start_date} 00:00:00", f"{end_date} 23:59:59")`.
3. Mark the survey step complete if part of a survey.
4. Format the dates for the template and return a confirmation or error message using the vacation template.

## Pseudocode
```python
async def handle_vacation(payload):
    try:
        start = payload["result"]["start_date"]
        end = payload["result"]["end_date"]
        await calendar.create_event(
            summary=f"Vacation: {payload['author']}",
            start_date=f"{start} 00:00:00",
            end_date=f"{end} 23:59:59",
        )
        await survey.mark_step(payload["userId"], "vacation")
        return {"output": templates.vacation(start, end)}
    except Exception:
        return {"output": "Спробуй трохи піздніше. Я тут пораюсь по хаті."}
```

## Tests
- Unit:
  - **Valid event** – mock `calendar.create_event` with payload `{ "summary": "Vacation: User", "start": "YYYY-MM-DD 00:00:00", "end": "YYYY-MM-DD 23:59:59" }` to return `{ "id": "vac1" }` and assert step marking.
  - **Calendar error** – mock `create_event` to raise and assert error message.
- End-to-end: simulate `/vacation` and verify the bot replies with the vacation summary.
- All tests must log inputs, steps, and outputs to a file for later review.