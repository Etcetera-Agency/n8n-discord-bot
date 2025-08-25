# Workload Today Command Implementation

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
- **Input**: `{ command: "survey", status: "step", result: { stepName: "workload_today", value: 8 } }`
- **Side Effects**: 
  - Updates Notion Workload DB with hours for current day
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
Заплановане навантаження у Понеділок: 8 год.
В щоденнику з понеділка до Понеділок: 8 год.
Капасіті на цей тиждень: 40 год.
#dev-serhii-shevchyk    15:30
```

```
Записав!
Заплановане навантаження у Понеділок: 0 год.
В щоденнику з понеділка до Понеділок: 0 год.
Капасіті на цей тиждень: 40 год.
#dev-serhii-shevchyk    09:15
```

## 3. Pseudocode (15 lines)

```python
def handle_workload_today(request):
    hours = int(request.result.value)
    user_name = get_user_name_from_channel(request.channelId)
    
    # Get workload DB record
    workload_page = notion_client.get_workload_by_name(user_name)
    if not workload_page:
        return {"output": "Користувача не знайдено в базі навантаження"}
    
    # Determine current day field
    today = datetime.now(ZoneInfo("Europe/Kyiv"))
    day_field = get_ukrainian_weekday(today) + "|number"
    
    # Update workload
    notion_client.update_workload_hours(workload_page.url, day_field, hours)
    
    # Mark step complete
    postgres_client.upsert_survey_step(request.channelId, "workload_today", completed=True)
    
    # Calculate totals and format response
    logged_hours = calculate_week_total(workload_page, today)
    return format_workload_response(today, hours, logged_hours, workload_page.capacity, request.channelName)
```

## 4. Request/Response Schema

### Request DTO
```python
@dataclass
class WorkloadTodayRequest:
    command: str  # "survey"
    status: str   # "step"
    result: dict  # {"stepName": "workload_today", "value": 8}
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
class WorkloadTodayResponse:
    output: str
    survey: str  # "continue" | "end"
```

**Response Schema**: `{ "output": "string", "survey": "continue" }`

## 5. Tests (pytest)

### Test Function Names:
- `test_workload_today_success_updates_notion_and_formats_response()`
- `test_workload_today_zero_hours_is_valid()`
- `test_workload_today_user_not_found_returns_error()`
- `test_workload_today_notion_update_failure_propagates_error()`
- `test_workload_today_marks_survey_step_complete()`
- `test_workload_today_calculates_week_total_correctly()`
- `test_workload_today_formats_ukrainian_weekday()`
- `test_workload_today_formats_footer_with_middle_dot()`

### Key Test Cases:
```python
def test_workload_today_success_updates_notion_and_formats_response():
    # Mock current time: Monday 15:30 Kyiv
    with freeze_time("2024-01-15 15:30:00", tz_offset=2):
        mock_notion.get_workload_by_name.return_value = MockWorkloadPage(
            url="workload-url",
            capacity=40,
            monday_hours=0
        )
        mock_get_user_name.return_value = "Сергій Шевчик"
        
        response = handle_workload_today(WorkloadTodayRequest(
            command="survey",
            status="step",
            result={"stepName": "workload_today", "value": 8},
            channelId="1362738788505485414",
            channelName="dev-serhii-shevchyk"
        ))
        
        expected_output = """Записав!
Заплановане навантаження у Понеділок: 8 год.
В щоденнику з понеділка до Понеділок: 8 год.
Капасіті на цей тиждень: 40 год.
#dev-serhii-shevchyk    15:30"""
        
        assert response.output == expected_output
        assert response.survey == "continue"
        
        # Verify Notion updates
        mock_notion.update_workload_hours.assert_called_with(
            "workload-url", "Понеділок|number", 8
        )
        
        # Verify survey step marked complete
        mock_postgres.upsert_survey_step.assert_called_with(
            "1362738788505485414", "workload_today", completed=True
        )

def test_workload_today_zero_hours_is_valid():
    with freeze_time("2024-01-15 09:15:00", tz_offset=2):
        mock_notion.get_workload_by_name.return_value = MockWorkloadPage(capacity=40)
        mock_get_user_name.return_value = "Test User"
        
        response = handle_workload_today(WorkloadTodayRequest(
            result={"stepName": "workload_today", "value": 0},
            channelName="test-channel"
        ))
        
        assert "0 год." in response.output
        assert response.survey == "continue"
        mock_postgres.upsert_survey_step.assert_called_with(
            ANY, "workload_today", completed=True
        )

def test_workload_today_calculates_week_total_correctly():
    with freeze_time("2024-01-17 10:00:00", tz_offset=2):  # Wednesday
        mock_notion.get_workload_by_name.return_value = MockWorkloadPage(
            monday_hours=8,
            tuesday_hours=6,
            wednesday_hours=0  # Will be updated to 7
        )
        
        response = handle_workload_today(WorkloadTodayRequest(
            result={"value": 7}
        ))
        
        # Should show total from Monday to Wednesday: 8 + 6 + 7 = 21
        assert "21 год." in response.output
```

## 6. Acceptance Criteria

- [ ] **Zero hours validation** - `value: 0` is valid and completes the step
- [ ] **Notion property updates** use exact day field format: `{Ukrainian_Day}|number`
- [ ] **Week total calculation** sums Monday through current day
- [ ] **Ukrainian weekday names** - Понеділок, Вівторок, Середа, Четвер, П'ятниця, Субота, Неділя
- [ ] **Survey step completion** upserts `workload_today` with `completed=true`
- [ ] **Response format** matches template exactly including newlines
- [ ] **Time formatting** as HH:MM in response
- [ ] **Channel name** without # prefix in response
- [ ] **Error handling** for missing user or Notion failures
- [ ] **Coverage ≥ 90%** for workload_today handler module