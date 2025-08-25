# Day Off This Week Command Implementation

## 1. What the n8n flow does

### n8n Node Sequence:
1. **Switch1** → Routes to "dayoff" branch when `/day_off/i.test(command + stepName)`
2. **Set day-off** → Sets instruction for day-off handling
3. **AI Agent** → Processes with tools:
   - `Create_Day-off_or_Vacation` → Creates all-day calendar events
   - `Survey_step_status` → Upserts completion status
4. **Basic LLM Chain** → Formats response as JSON
5. **toJSON** → Parses and validates JSON output

### Branching Logic:
- **Input**: `{ command: "survey", status: "step", result: { stepName: "day_off_thisweek", value: { values: ["2024-01-20"] } } }`
- **Side Effects**: 
  - Creates Google Calendar all-day events for each date
  - Marks survey step as completed
- **Special Cases**:
  - `value: "Nothing"` → No days off, mark complete
  - `value: { values: [...] }` → Create events for each date

## 2. Response Templates (exact)

### Day-off One Day Template
```
Записав!
Вихідний: {date}
#{channel}    {time}
```

### Day-off Multiple Days Template
```
Записав!
Вихідні: {date_list}
#{channel}    {time}
```

### Day-off None Template
```
Записав!
Вихідних немає
#{channel}    {time}
```

### Examples:
```
Записав!
Вихідний: 2024-01-20
#dev-serhii-shevchyk    15:30
```

```
Записав!
Вихідні: 2024-01-20, 2024-01-21
#dev-serhii-shevchyk    15:30
```

```
Записав!
Вихідних немає
#dev-serhii-shevchyk    15:30
```

## 3. Pseudocode (15 lines)

```python
def handle_day_off_thisweek(request):
    result_value = request.result.value
    user_name = get_user_name_from_channel(request.channelId)
    
    # Handle "Nothing" case
    if result_value == "Nothing":
        postgres_client.upsert_survey_step(request.channelId, "day_off_thisweek", completed=True)
        return format_day_off_response("none", [], request.channelName)
    
    # Extract dates from value.values
    dates = result_value.get("values", [])
    
    # Create calendar events for each date
    for date_str in dates:
        gcal_client.create_all_day_event(
            summary=f"Day off: {user_name}",
            start_date=date_str,
            end_date=date_str
        )
    
    # Mark step complete
    postgres_client.upsert_survey_step(request.channelId, "day_off_thisweek", completed=True)
    
    return format_day_off_response("multiple" if len(dates) > 1 else "single", dates, request.channelName)
```

## 4. Request/Response Schema

### Request DTO
```python
@dataclass
class DayOffThisweekRequest:
    command: str  # "survey"
    status: str   # "step"
    result: dict  # {"stepName": "day_off_thisweek", "value": {"values": ["2024-01-20"]}}
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
class DayOffThisweekResponse:
    output: str
    survey: str  # "continue" | "end"
```

**Response Schema**: `{ "output": "string", "survey": "continue" }`

## 5. Tests (pytest)

### Test Function Names:
- `test_day_off_formats_footer_with_middle_dot()`
- `test_day_off_thisweek_single_day_creates_event_and_formats_response()`
- `test_day_off_thisweek_multiple_days_creates_events_and_formats_response()`
- `test_day_off_thisweek_nothing_marks_complete_no_events()`
- `test_day_off_thisweek_gcal_failure_propagates_error()`
- `test_day_off_thisweek_marks_survey_step_complete()`
- `test_day_off_thisweek_formats_date_list_correctly()`
- `test_day_off_thisweek_creates_allday_events_with_correct_summary()`

### Key Test Cases:
```python
def test_day_off_thisweek_single_day_creates_event_and_formats_response():
    with freeze_time("2024-01-15 15:30:00", tz_offset=2):
        mock_get_user_name.return_value = "Сергій Шевчик"
        
        response = handle_day_off_thisweek(DayOffThisweekRequest(
            command="survey",
            status="step",
            result={
                "stepName": "day_off_thisweek",
                "value": {"values": ["2024-01-20"]}
            },
            channelId="1362738788505485414",
            channelName="dev-serhii-shevchyk"
        ))
        
        expected_output = """Записав!
Вихідний: 2024-01-20
#dev-serhii-shevchyk    15:30"""
        
        assert response.output == expected_output
        assert response.survey == "continue"
        
        # Verify calendar event creation
        mock_gcal.create_all_day_event.assert_called_once_with(
            summary="Day off: Сергій Шевчик",
            start_date="2024-01-20",
            end_date="2024-01-20"
        )
        
        # Verify survey step marked complete
        mock_postgres.upsert_survey_step.assert_called_with(
            "1362738788505485414", "day_off_thisweek", completed=True
        )

def test_day_off_thisweek_multiple_days_creates_events_and_formats_response():
    with freeze_time("2024-01-15 15:30:00", tz_offset=2):
        mock_get_user_name.return_value = "Test User"
        
        response = handle_day_off_thisweek(DayOffThisweekRequest(
            result={
                "stepName": "day_off_thisweek",
                "value": {"values": ["2024-01-20", "2024-01-21"]}
            },
            channelName="test-channel"
        ))
        
        expected_output = """Записав!
Вихідні: 2024-01-20, 2024-01-21
#test-channel    15:30"""
        
        assert response.output == expected_output
        
        # Verify multiple calendar events created
        assert mock_gcal.create_all_day_event.call_count == 2
        mock_gcal.create_all_day_event.assert_any_call(
            summary="Day off: Test User",
            start_date="2024-01-20",
            end_date="2024-01-20"
        )
        mock_gcal.create_all_day_event.assert_any_call(
            summary="Day off: Test User",
            start_date="2024-01-21",
            end_date="2024-01-21"
        )

def test_day_off_thisweek_nothing_marks_complete_no_events():
    with freeze_time("2024-01-15 15:30:00", tz_offset=2):
        response = handle_day_off_thisweek(DayOffThisweekRequest(
            result={
                "stepName": "day_off_thisweek",
                "value": "Nothing"
            },
            channelName="test-channel"
        ))
        
        expected_output = """Записав!
Вихідних немає
#test-channel    15:30"""
        
        assert response.output == expected_output
        assert response.survey == "continue"
        
        # Verify no calendar events created
        mock_gcal.create_all_day_event.assert_not_called()
        
        # Verify survey step still marked complete
        mock_postgres.upsert_survey_step.assert_called_with(
            ANY, "day_off_thisweek", completed=True
        )

def test_day_off_thisweek_creates_allday_events_with_correct_summary():
    mock_get_user_name.return_value = "Іван Петренко"
    
    handle_day_off_thisweek(DayOffThisweekRequest(
        result={"value": {"values": ["2024-01-20"]}}
    ))
    
    mock_gcal.create_all_day_event.assert_called_with(
        summary="Day off: Іван Петренко",
        start_date="2024-01-20",
        end_date="2024-01-20"
    )
```

## 6. Acceptance Criteria

- [ ] **"Nothing" handling** - Marks step complete without creating events
- [ ] **Single day format** - Uses "Вихідний:" for one date
- [ ] **Multiple days format** - Uses "Вихідні:" with comma-separated dates
- [ ] **All-day events** - Creates Google Calendar events with correct date range
- [ ] **Event summary** - Uses format "Day off: {user_name}"
- [ ] **Survey step completion** upserts `day_off_thisweek` with `completed=true`
- [ ] **Response format** matches templates exactly including newlines
- [ ] **Time formatting** as HH:MM in response
- [ ] **Channel name** without # prefix in response
- [ ] **Error handling** for Google Calendar API failures
- [ ] **Coverage ≥ 90%** for day_off_thisweek handler module