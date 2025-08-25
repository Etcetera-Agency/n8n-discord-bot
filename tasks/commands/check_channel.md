# Check Channel Command Implementation

## 1. What the n8n flow does

### n8n Node Sequence:
1. **Switch** → Routes to "check_channel" branch when `command.includes("check_channel")`
2. **Postgres get steps** → Selects from `n8n_survey_steps_missed` WHERE `session_id = channelId`
3. **Code** → JavaScript logic for week calculation and pending steps:
   - Calculates Monday start of week (dow = (now.getDay() + 6) % 7)
   - Creates schedule object for each day
   - Determines pending steps based on completion status
   - Excludes steps completed today from today's list
4. **Respond chanel found** → Returns response with steps data

### Branching Logic:
- **Input**: `{ command: "check_channel", channelId: "..." }`
- **Side Effects**: None (read-only operation)
- **Algorithm**:
  1. Compute `week_start = Monday 00:00 (Europe/Kyiv)`
  2. Query latest weekly records per `step_name` for `session_id = channelId`
  3. A step is **pending** if no record exists this week OR latest record has `completed=false`
  4. Exclude steps completed **today** from today's list

## 2. Response Templates (exact)

### Check Channel Response
```json
{
  "output": "Перевірка каналу завершена",
  "steps": ["workload_today", "connects_thisweek"]
}
```

### Examples:
```json
{
  "output": "Знайдено незавершені кроки для каналу",
  "steps": ["workload_today", "workload_nextweek", "day_off_thisweek"]
}
```

```json
{
  "output": "Всі кроки опитування завершені",
  "steps": []
}
```

## 3. Pseudocode (15 lines)

```python
def handle_check_channel(request):
    channel_id = request.channelId
    
    # Calculate week start (Monday 00:00 Kyiv)
    now = datetime.now(ZoneInfo("Europe/Kyiv"))
    days_since_monday = (now.weekday()) % 7
    week_start = now.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=days_since_monday)
    
    # Query latest weekly records per step
    records = postgres_client.get_weekly_steps(channel_id, week_start)
    
    # Determine pending steps
    all_steps = ["workload_today", "workload_nextweek", "connects_thisweek", "day_off_nextweek", "day_off_thisweek"]
    pending_steps = []
    
    for step in all_steps:
        record = records.get(step)
        if not record or not record.completed:
            # Exclude today's completed steps from today's list
            if not (record and record.completed and record.updated.date() == now.date()):
                pending_steps.append(step)
    
    return {"output": "Перевірка каналу завершена", "steps": pending_steps}
```

## 4. Request/Response Schema

### Request DTO
```python
@dataclass
class CheckChannelRequest:
    command: str  # "check_channel"
    channelId: str
    userId: str
    sessionId: str
    author: str
    channelName: str
    timestamp: int
```

### Response DTO
```python
@dataclass
class CheckChannelResponse:
    output: bool
    steps: List[str]
```

**Response Schema**: `{ "output": "string", "steps": ["string"] }`

## 5. Tests (pytest)

### Test Function Names:
- `test_check_channel_weekly_pending_excludes_today()`
- `test_check_channel_all_completed_returns_empty_steps()`
- `test_check_channel_no_records_returns_all_steps()`
- `test_check_channel_week_boundary_monday_00_00_kyiv()`
- `test_check_channel_week_boundary_uses_zoneinfo_kyiv()`
- `test_check_channel_completed_today_excluded_from_pending()`
- `test_check_channel_completed_yesterday_included_in_pending()`
- `test_check_channel_postgres_failure_propagates_error()`

### Key Test Cases:
```python
def test_check_channel_weekly_pending_excludes_today():
    # Mock current time: Tuesday 15:30 Kyiv
    from datetime import datetime
    from zoneinfo import ZoneInfo
    now = datetime(2024, 1, 16, 15, 30, tzinfo=ZoneInfo("Europe/Kyiv"))
    with freeze_time(now):
        # Mock DB records
        mock_postgres.get_weekly_steps.return_value = {
            "workload_today": MockRecord(completed=True, updated=datetime(2024, 1, 16, 10, 0)),  # Today
            "workload_nextweek": MockRecord(completed=False, updated=datetime(2024, 1, 15, 14, 0)),  # Yesterday
            # No record for connects_thisweek
        }
        
        response = handle_check_channel(CheckChannelRequest(
            command="check_channel",
            channelId="1362738788505485414"
        ))
        
        # workload_today excluded (completed today)
        # workload_nextweek included (not completed)
        # connects_thisweek included (no record)
        expected_steps = ["workload_nextweek", "connects_thisweek", "day_off_nextweek", "day_off_thisweek"]
        assert response.steps == expected_steps

def test_check_channel_week_boundary_monday_00_00_kyiv():
    # Test Monday 00:00 boundary
    from datetime import datetime
    from zoneinfo import ZoneInfo
    now = datetime(2024, 1, 15, 0, 0, tzinfo=ZoneInfo("Europe/Kyiv"))
    with freeze_time(now):
        mock_postgres.get_weekly_steps.return_value = {}
        
        response = handle_check_channel(CheckChannelRequest(channelId="test"))
        
        # Verify week_start calculation
        expected_week_start = datetime(2024, 1, 15, 0, 0, 0, tzinfo=ZoneInfo("Europe/Kyiv"))
        mock_postgres.get_weekly_steps.assert_called_with("test", expected_week_start)

def test_check_channel_all_completed_returns_empty_steps():
    from datetime import datetime
    from zoneinfo import ZoneInfo
    now = datetime(2024, 1, 16, 15, 30, tzinfo=ZoneInfo("Europe/Kyiv"))
    with freeze_time(now):
        # All steps completed this week
        mock_postgres.get_weekly_steps.return_value = {
            step: MockRecord(completed=True, updated=datetime(2024, 1, 15, 10, 0))
            for step in ["workload_today", "workload_nextweek", "connects_thisweek", "day_off_nextweek", "day_off_thisweek"]
        }
        
        response = handle_check_channel(CheckChannelRequest(channelId="test"))
        
        assert response.steps == []
        assert response.output == "Перевірка каналу завершена"
```

## 6. Acceptance Criteria

- [ ] **Week calculation** uses Europe/Kyiv timezone with Monday 00:00 start
- [ ] **Database query** uses exact SQL pattern from schema: `SELECT DISTINCT ON (step_name) ...`
- [ ] **Pending logic** correctly identifies incomplete or missing steps
- [ ] **Today exclusion** removes steps completed today from pending list
- [ ] **Step enumeration** returns the configured set of required steps (at minimum: workload_today, workload_nextweek, connects_thisweek, day_off_nextweek, day_off_thisweek); the list may expand via config.
- [ ] **Response schema** includes both `output` string and `steps` array
- [ ] **Week boundary tests** validate Monday 00:00 Kyiv calculations using `zoneinfo`
- [ ] **Error handling** for PostgreSQL failures
- [ ] **Coverage ≥ 90%** for check_channel handler module