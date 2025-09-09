# Task 02: Calendar connector

## Goal
Implement an async client for the calendar service so handlers can create day-off and vacation events without n8n.

## Supported operations
1. **Create day-off event**
   - summary: `"Day-off: {user.name}"`
   - start/end dates are the same (all-day event)
2. **Create vacation event**
   - summary: `"Vacation: {user.name}"`
   - start/end timestamps span the chosen range (00:00–23:59)

## Expected inputs and outputs
### Create single day-off
Request to `/events`:
```json
{
  "summary": "Day-off: Roman Lernichenko",
  "start": {"date": "2024-02-05"},
  "end": {"date": "2024-02-05"}
}
```
Calendar response:
```json
{ "id": "CAL_EVENT_ID" }
```
Normalized output:
```json
{ "status": "ok", "event_id": "CAL_EVENT_ID" }
```

### Create vacation range
Request to `/events`:
```json
{
  "summary": "Vacation: Roman Lernichenko",
  "start": {"dateTime": "2024-02-05T00:00:00", "timeZone": "Europe/Kyiv"},
  "end": {"dateTime": "2024-02-10T23:59:59", "timeZone": "Europe/Kyiv"}
}
```
Failure template for any operation:
```json
{ "status": "error", "message": "calendar unreachable" }
```

## Pseudocode
```
def base_headers():
    token = os.environ["CALENDAR_TOKEN"]
    return {"Authorization": f"Bearer {token}"}

async def create_event(summary, start, end):
    payload = {"summary": summary, "start": start, "end": end}
    async with aiohttp.post(CALENDAR_URL, headers=base_headers(), json=payload) as resp:
        data = await resp.json()
        if resp.status != 200:
            return {"status": "error", "message": data.get("error")}
        return {"status": "ok", "event_id": data["id"]}
```

## Testing
- Unit tests should mock the HTTP client to assert headers, payload shapes, and error handling for both day-off and vacation events.
- End-to-end tests should mock the calendar API and verify handlers forward the connector’s success and failure responses.
- All tests must log inputs, steps, and outputs to a file for later review.
