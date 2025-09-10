# Task 11: Day Off Handler

## Goal
Implement `handle_day_off` to record days off for either the current or upcoming week.

## Business Logic
- Read an array of dates or the string `"Nothing"` from the payload.
- When dates are provided, create a calendar event for each date with:
  - `summary`: `"Day-off: {user.name}"`
  - `start`: `YYYY-MM-DD`
  - `end`:   `YYYY-MM-DD`
- When the user selects `"Nothing"`, skip calendar writes and mark the step complete.
- Mark the corresponding survey step (`day_off_thisweek` or `day_off_nextweek`) as completed.
- Choose response template based on whether zero, one, or many dates were provided and whether the command targeted this week or next week.
- Format dates in responses using a helper that outputs `DD MMMM YY`.
- Any calendar failure returns the generic error message.
- when write to n8n_survey_steps_missed session_id is always channel_id only.


### Input Variants
- **day_off_thisweek** – `result.value` is an array of dates or the string `"Nothing"`.
- **day_off_nextweek** – same structure as above for next week.
- **Generic failure** – any calendar error triggers the fallback message.

#### Example Payload (`day_off_nextweek`)
```json
{
  "command": "day_off_nextweek",
  "status": "ok",
  "message": "",
  "result": {
    "value": ["YYYY-MM-DD", "YYYY-MM-DD"]
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
- One date: `{ "output": "Вихідний: {DD MMMM YY} записано.\nНе забудь попередити клієнтів." }`
- Many dates: `{ "output": "Вихідні: {DD MMMM YY}, {DD MMMM YY} записані.\nНе забудь попередити клієнтів." }`
- No dates (`"Nothing"`): `{ "output": "Записав! Вихідних нема" }`
- Error: `{ "output": "Спробуй трохи піздніше. Я тут пораюсь по хаті." }`

## Steps
1. Extract dates from `payload["result"]["value"]`.
2. If the value is `"Nothing"` or an empty list, mark the step and return the "no dates" template.
3. Otherwise, call `calendar.create_event("Day-off: {user.name}", day, day)` for each date.
4. Mark the survey step complete.
5. Choose the one-date or many-date template, formatting dates as `DD MMMM YY`, and return it.
6. On calendar failure, return the error message.

## Pseudocode
```python
async def handle_day_off(payload):
    try:
        value = payload["result"]["value"]
        step = payload["command"]
        if value == "Nothing" or not value:
            await survey.mark_step(payload["userId"], step)
            return {"output": templates.dayoff_none}
        for day in value:
            await calendar.create_event(
                summary=f"Day-off: {payload['author']}",
                start_date=day,
                end_date=day,
            )
        await survey.mark_step(payload["userId"], step)
        if len(value) == 1:
            return {"output": templates.dayoff_one(value[0])}
        return {"output": templates.dayoff_many(value)}
    except Exception:
        return {"output": "Спробуй трохи піздніше. Я тут пораюсь по хаті."}
```

## Tests
- Unit:
  - **No dates** – payload with `"Nothing"` should mark step without calling calendar.
  - **One date** – mock `calendar.create_event` with payload `{ "summary": "Day-off: User", "start": "YYYY-MM-DD", "end": "YYYY-MM-DD" }` to return `{ "id": "event1" }` and assert `dayoff_one` template.
  - **Many dates** – mock multiple `create_event` calls and assert `dayoff_many` template.
  - **Calendar error** – mock `create_event` to raise and assert error message.
- End-to-end: simulate `/day_off_thisweek` and `/day_off_nextweek` payloads and verify responses.
- All tests must log inputs, steps, and outputs to a file for later review.