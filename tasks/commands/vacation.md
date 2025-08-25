# Vacation Command Implementation

## 1. What the n8n flow does

### n8n Node Sequence:
1. **Switch1** → Routes to "vacation" branch when `/vacation/i.test(command + stepName)`
2. **Set vacation** → Sets instruction for vacation handling
3. **AI Agent** → Processes with tools:
   - `Create_Day-off_or_Vacation` → Creates all-day calendar event for date range
4. **Basic LLM Chain** → Formats response as JSON
5. **toJSON** → Parses and validates JSON output

### Branching Logic:
- **Input**: `{ command: "survey", status: "step", result: { stepName: "vacation", start: "2024-02-01", end: "2024-02-14" } }`
- **Side Effects**: 
  - Creates Google Calendar all-day event spanning the date range
  - Does not mark survey step (vacation is not a tracked survey step)

## 2. Response Templates (exact)

### Vacation Template
```
Записав!
Відпустка: {start_date} - {end_date}
#{channel}    {time}
```

### Examples:
```
Записав!
Відпустка: 2024-02-01 - 2024-02-14
#dev-serhii-shevchyk    15:30
```

```
Записав!
Відпустка: 2024-03-15 - 2024-03-22
#dev-serhii-shevchyk    11:45
```

## 3. Pseudocode (15 lines)

```python
def handle_vacation(request):
    start_date = request.result.start
    end_date = request.result.end
    user_name = get_user_name_from_channel(request.channelId)
    
    # Create calendar event for vacation period
    gcal_client.create_all_day_event(
        summary=f"Vacation: {user_name}",
        start_date=f"{start_date} 00:00:00",
        end_date=f"{end_date} 23:59:59"
    )
    
    # Format response
    return {
        "output": format_vacation_response(start_date, end_date, request.channelName)
    }
```

## 4. Request/Response Schema

### Request DTO
```python
@dataclass
class VacationRequest:
    command: str  # "survey"
    status: str   # "step"
    result: dict  # {"stepName": "vacation", "start": "2024-02-01", "end": "2024-02-14"}
    userId: str
    channelId: str
    sessionId: str
    author: str
    channelName: str
    timestamp: int
```

### Response DTO
```python
@dataclass
class VacationResponse:
    output: str
```

**Response Schema**: `{ "output": "string" }`

## 5. Tests (pytest)

### Test Function Names:
- `test_vacation_formats_footer_with_middle_dot()`
- `test_vacation_creates_calendar_event_and_formats_response()`
- `test_vacation_single_day_period_works()`
- `test_vacation_gcal_failure_propagates_error()`
- `test_vacation_formats_date_range_correctly()`
- `test_vacation_creates_event_with_correct_summary()`
- `test_vacation_uses_full_day_time_range()`
- `test_vacation_does_not_mark_survey_step()`

### Key Test Cases:
```python
def test_vacation_creates_calendar_event_and_formats_response():
    with freeze_time("2024-01-15 15:30:00", tz_offset=2):
        mock_get_user_name.return_value = "Сергій Шевчик"
        
        response = handle_vacation(VacationRequest(
            command="survey",
            status="step",
            result={
                "stepName": "vacation",
                "start": "2024-02-01",
                "end": "2024-02-14"
            },
            channelId="1362738788505485414",
            channelName="dev-serhii-shevchyk"
        ))
        
        expected_output = """Записав!
Відпустка: 2024-02-01 - 2024-02-14
#dev-serhii-shevchyk    15:30"""
        
        assert response.output == expected_output
        
        # Verify calendar event creation
        mock_gcal.create_all_day_event.assert_called_once_with(
            summary="Vacation: Сергій Шевчик",
            start_date="2024-02-01 00:00:00",
            end_date="2024-02-14 23:59:59"
        )

def test_vacation_single_day_period_works():
    with freeze_time("2024-01-15 11:45:00", tz_offset=2):
        mock_get_user_name.return_value = "Test User"
        
        response = handle_vacation(VacationRequest(
            result={
                "start": "2024-02-15",
                "end": "2024-02-15"
            },
            channelName="test-channel"
        ))
        
        expected_output = """Записав!
Відпустка: 2024-02-15 - 2024-02-15
#test-channel    11:45"""
        
        assert response.output == expected_output
        
        # Verify single day vacation event
        mock_gcal.create_all_day_event.assert_called_once_with(
            summary="Vacation: Test User",
            start_date="2024-02-15 00:00:00",
            end_date="2024-02-15 23:59:59"
        )

def test_vacation_uses_full_day_time_range():
    handle_vacation(VacationRequest(
        result={
            "start": "2024-03-01",
            "end": "2024-03-07"
        }
    ))
    
    # Verify full day time range
    call_args = mock_gcal.create_all_day_event.call_args
    assert call_args[1]["start_date"] == "2024-03-01 00:00:00"
    assert call_args[1]["end_date"] == "2024-03-07 23:59:59"

def test_vacation_does_not_mark_survey_step():
    handle_vacation(VacationRequest(
        result={"start": "2024-02-01", "end": "2024-02-14"},
        channelId="test-channel"
    ))
    
    # Vacation is not a tracked survey step
    mock_postgres.upsert_survey_step.assert_not_called()

def test_vacation_creates_event_with_correct_summary():
    mock_get_user_name.return_value = "Іван Петренко"
    
    handle_vacation(VacationRequest(
        result={"start": "2024-02-01", "end": "2024-02-14"}
    ))
    
    mock_gcal.create_all_day_event.assert_called_with(
        summary="Vacation: Іван Петренко",
        start_date="2024-02-01 00:00:00",
        end_date="2024-02-14 23:59:59"
    )

def test_vacation_gcal_failure_propagates_error():
    mock_gcal.create_all_day_event.side_effect = Exception("Calendar API error")
    
    with pytest.raises(Exception, match="Calendar API error"):
        handle_vacation(VacationRequest(
            result={"start": "2024-02-01", "end": "2024-02-14"}
        ))
```

## 6. Acceptance Criteria

- [ ] **Date range event** - Creates single Google Calendar event spanning start to end date
- [ ] **Full day coverage** - Uses "00:00:00" start time and "23:59:59" end time
- [ ] **Event summary** - Uses format "Vacation: {user_name}"
- [ ] **Single day support** - Handles start_date == end_date correctly
- [ ] **No survey tracking** - Does not call `upsert_survey_step` (vacation is not a tracked step)
- [ ] **Response format** matches template exactly including newlines
- [ ] **Time formatting** as HH:MM in response
- [ ] **Channel name** without # prefix in response
- [ ] **Error handling** for Google Calendar API failures
- [ ] **Coverage ≥ 90%** for vacation handler module