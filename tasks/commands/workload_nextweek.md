# Workload Next Week Command Implementation

## 1. What the n8n flow does

### n8n Node Sequence:
1. **Switch1** → Routes to "workload" branch when `/workload/i.test(command + stepName)`
2. **Set workload** → Sets instruction for workload handling
3. **AI Agent** → Processes with tools:
   - `Get_Workload_DB_by_name` → Searches Workload DB by user name
   - `Write_plan_hours_to_Workload_DB` → Updates day field with hours
   - `Write_capacity_to_Workload_DB` → Updates capacity if present
   - `Survey_step_status` → Upserts completion status
4. **Basic LLM Chain** → Formats response as JSON
5. **toJSON** → Parses and validates JSON output

### Branching Logic:
- **Input**: `{ command: "survey", status: "step", result: { stepName: "workload_nextweek", value: 6 } }`
- **Side Effects**: 
  - Updates Notion Workload DB with hours for specified day
  - Updates capacity if provided
  - Marks survey step as completed
- **Important**: `value: 0` is valid and marks step complete

## 2. Response Templates (exact)

### Workload Confirmation Template
```
Записав!
Заплановане навантаження у {Weekday}: {hours} год.
В щоденнику з понеділка до {Weekday}: {logged_hours} год.
Капасіті на цей тиждень: {capacity} год.
#{channel}    {time}
```

### Examples:
```
Записав!
Заплановане навантаження у Вівторок: 6 год.
В щоденнику з понеділка до Вівторок: 14 год.
Капасіті на цей тиждень: 40 год.
#dev-serhii-shevchyk    15:30
```

```
Записав!
Заплановане навантаження у П'ятниця: 0 год.
В щоденнику з понеділка до П'ятниця: 32 год.
Капасіті на цей тиждень: 40 год.
#dev-serhii-shevchyk    11:45
```

## 3. Pseudocode (15 lines)

```python
def handle_workload_nextweek(request):
    hours = int(request.result.value)
    user_name = get_user_name_from_channel(request.channelId)
    
    # Get workload DB record
    workload_page = notion_client.get_workload_by_name(user_name)
    if not workload_page:
        return {"output": "Користувача не знайдено в базі навантаження"}
    
    # Determine target day (next working day or specified day)
    target_day = determine_next_workload_day()
    day_field = get_ukrainian_weekday(target_day) + "|number"
    
    # Update workload
    notion_client.update_workload_hours(workload_page.url, day_field, hours)
    
    # Mark step complete
    postgres_client.upsert_survey_step(request.channelId, "workload_nextweek", completed=True)
    
    # Calculate totals and format response
    logged_hours = calculate_week_total_through_day(workload_page, target_day)
    return format_workload_response(target_day, hours, logged_hours, workload_page.capacity, request.channelName)
```

## 4. Request/Response Schema

### Request DTO
```python
@dataclass
class WorkloadNextweekRequest:
    command: str  # "survey"
    status: str   # "step"
    result: dict  # {"stepName": "workload_nextweek", "value": 6}
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
class WorkloadNextweekResponse:
    output: str
    survey: str  # "continue" | "end"
```

**Response Schema**: `{ "output": "string", "survey": "continue" }`

## 5. Tests (pytest)

### Test Function Names:
- `test_workload_nextweek_success_updates_notion_and_formats_response()`
- `test_workload_nextweek_zero_hours_is_valid()`
- `test_workload_nextweek_user_not_found_returns_error()`
- `test_workload_nextweek_notion_update_failure_propagates_error()`
- `test_workload_nextweek_marks_survey_step_complete()`
- `test_workload_nextweek_calculates_cumulative_total()`
- `test_workload_nextweek_determines_correct_target_day()`

### Key Test Cases:
```python
def test_workload_nextweek_success_updates_notion_and_formats_response():
    # Mock current time: Monday, planning for Tuesday
    with freeze_time("2024-01-15 15:30:00", tz_offset=2):
        mock_notion.get_workload_by_name.return_value = MockWorkloadPage(
            url="workload-url",
            capacity=40,
            monday_hours=8,
            tuesday_hours=0  # Will be updated
        )
        mock_get_user_name.return_value = "Сергій Шевчик"
        mock_determine_next_workload_day.return_value = datetime(2024, 1, 16)  # Tuesday
        
        response = handle_workload_nextweek(WorkloadNextweekRequest(
            command="survey",
            status="step",
            result={"stepName": "workload_nextweek", "value": 6},
            channelId="1362738788505485414",
            channelName="dev-serhii-shevchyk"
        ))
        
        expected_output = """Записав!
Заплановане навантаження у Вівторок: 6 год.
В щоденнику з понеділка до Вівторок: 14 год.
Капасіті на цей тиждень: 40 год.
#dev-serhii-shevchyk    15:30"""
        
        assert response.output == expected_output
        assert response.survey == "continue"
        
        # Verify Notion updates
        mock_notion.update_workload_hours.assert_called_with(
            "workload-url", "Вівторок|number", 6
        )
        
        # Verify survey step marked complete
        mock_postgres.upsert_survey_step.assert_called_with(
            "1362738788505485414", "workload_nextweek", completed=True
        )

def test_workload_nextweek_calculates_cumulative_total():
    with freeze_time("2024-01-17 10:00:00", tz_offset=2):  # Wednesday
        mock_notion.get_workload_by_name.return_value = MockWorkloadPage(
            monday_hours=8,
            tuesday_hours=6,
            wednesday_hours=7,
            thursday_hours=0  # Will be updated to 5
        )
        mock_determine_next_workload_day.return_value = datetime(2024, 1, 18)  # Thursday
        
        response = handle_workload_nextweek(WorkloadNextweekRequest(
            result={"value": 5}
        ))
        
        # Should show total from Monday to Thursday: 8 + 6 + 7 + 5 = 26
        assert "26 год." in response.output
        assert "Четвер: 5 год." in response.output

def test_workload_nextweek_determines_correct_target_day():
    # Test different scenarios for next workload day
    test_cases = [
        ("2024-01-15", "Monday", "Tuesday"),    # Monday -> Tuesday
        ("2024-01-16", "Tuesday", "Wednesday"), # Tuesday -> Wednesday
        ("2024-01-19", "Friday", "Monday"),     # Friday -> Next Monday
    ]
    
    for date_str, current_day, expected_day in test_cases:
        with freeze_time(f"{date_str} 10:00:00", tz_offset=2):
            target_day = determine_next_workload_day()
            assert get_ukrainian_weekday(target_day) == get_ukrainian_name(expected_day)

def test_workload_nextweek_zero_hours_is_valid():
    with freeze_time("2024-01-15 09:15:00", tz_offset=2):
        mock_notion.get_workload_by_name.return_value = MockWorkloadPage(capacity=40)
        mock_determine_next_workload_day.return_value = datetime(2024, 1, 16)
        
        response = handle_workload_nextweek(WorkloadNextweekRequest(
            result={"stepName": "workload_nextweek", "value": 0}
        ))
        
        assert "0 год." in response.output
        assert response.survey == "continue"
        mock_postgres.upsert_survey_step.assert_called_with(
            ANY, "workload_nextweek", completed=True
        )
```

## 6. Acceptance Criteria

- [ ] **Zero hours validation** - `value: 0` is valid and completes the step
- [ ] **Target day determination** - Logic for next working day or specified day
- [ ] **Notion property updates** use exact day field format: `{Ukrainian_Day}|number`
- [ ] **Cumulative total calculation** sums Monday through target day
- [ ] **Ukrainian weekday names** - Понеділок, Вівторок, Середа, Четвер, П'ятниця, Субота, Неділя
- [ ] **Survey step completion** upserts `workload_nextweek` with `completed=true`
- [ ] **Response format** matches template exactly including newlines
- [ ] **Time formatting** as HH:MM in response
- [ ] **Channel name** without # prefix in response
- [ ] **Error handling** for missing user or Notion failures
- [ ] **Coverage ≥ 90%** for workload_nextweek handler module