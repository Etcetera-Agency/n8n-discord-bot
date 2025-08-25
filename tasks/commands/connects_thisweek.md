# Connects This Week Command Implementation

## 1. What the n8n flow does

### n8n Node Sequence:
1. **Switch1** → Routes to "connects" branch when `/connects/i.test(command + stepName)`
2. **Set connects** → Sets instruction for connects handling
3. **AI Agent** → Processes with tools:
   - `Survey_step_status` → Upserts completion status
   - `Send_connects_to_db` → HTTP POST to external service
   - `Get_Profile_stats_DB_by_name` → Searches Profile Stats DB
   - `Write_connects_to_Profile_stats_DB` → Updates Notion (non-fatal if fails)
4. **Basic LLM Chain** → Formats response as JSON
5. **toJSON** → Parses and validates JSON output

### Branching Logic:
- **Input**: `{ command: "survey", status: "step", result: { stepName: "connects_thisweek", value: 5 } }`
- **Side Effects**: 
  - HTTP POST to `https://tech2.etcetera.kiev.ua/set-db-connects`
  - Updates Notion Profile Stats DB (if record exists)
  - Marks survey step as completed
- **Important**: Notion write failure is **non-fatal**

## 2. Response Templates (exact)

### Connects Template
```
Записав!
Коннекти на цьому тижні: {connects}
#{channel}    {time}
```

### Examples:
```
Записав!
Коннекти на цьому тижні: 5
#dev-serhii-shevchyk    15:30
```

```
Записав!
Коннекти на цьому тижні: 0
#dev-serhii-shevchyk    11:45
```

## 3. Pseudocode (15 lines)

```python
def handle_connects_thisweek(request):
    connects = int(request.result.value)
    user_name = get_user_name_from_channel(request.channelId)
    
    # Mark step complete first
    postgres_client.upsert_survey_step(request.channelId, "connects_thisweek", completed=True)
    
    # Send to external HTTP service
    http_client.post_connects_to_db(name=user_name, connects=connects)
    
    # Try to update Notion Profile Stats (non-fatal)
    try:
        profile_page = notion_client.get_profile_stats_by_name(user_name)
        if profile_page:  # Only update if record exists
            notion_client.update_connects(profile_page.url, connects)
    except Exception as e:
        logger.warning(f"Notion connects update failed (non-fatal): {e}")
    
    # Format response
    return format_connects_response(connects, request.channelName)
```

## 4. Request/Response Schema

### Request DTO
```python
@dataclass
class ConnectsThisweekRequest:
    command: str  # "survey"
    status: str   # "step"
    result: dict  # {"stepName": "connects_thisweek", "value": 5}
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
class ConnectsThisweekResponse:
    output: str
    survey: str  # "continue" | "end"
```

**Response Schema**: `{ "output": "string", "survey": "continue" }`

## 5. Tests (pytest)

### Test Function Names:
- `test_connects_thisweek_success_updates_all_services()`
- `test_connects_thisweek_zero_connects_is_valid()`
- `test_connects_thisweek_http_failure_propagates_error()`
- `test_connects_thisweek_notion_failure_non_fatal()`
- `test_connects_thisweek_no_profile_page_continues_normally()`
- `test_connects_thisweek_marks_survey_step_complete()`
- `test_connects_thisweek_formats_response_correctly()`

### Key Test Cases:
```python
def test_connects_thisweek_success_updates_all_services():
    with freeze_time("2024-01-15 15:30:00", tz_offset=2):
        mock_get_user_name.return_value = "Сергій Шевчик"
        mock_notion.get_profile_stats_by_name.return_value = MockProfilePage(
            url="profile-url"
        )
        
        response = handle_connects_thisweek(ConnectsThisweekRequest(
            command="survey",
            status="step",
            result={"stepName": "connects_thisweek", "value": 5},
            channelId="1362738788505485414",
            channelName="dev-serhii-shevchyk"
        ))
        
        expected_output = """Записав!
Коннекти на цьому тижні: 5
#dev-serhii-shevchyk    15:30"""
        
        assert response.output == expected_output
        assert response.survey == "continue"
        
        # Verify HTTP call
        mock_http.post_connects_to_db.assert_called_once_with(
            name="Сергій Шевчик",
            connects=5
        )
        
        # Verify Notion update
        mock_notion.update_connects.assert_called_once_with(
            "profile-url", 5
        )
        
        # Verify survey step marked complete
        mock_postgres.upsert_survey_step.assert_called_with(
            "1362738788505485414", "connects_thisweek", completed=True
        )

def test_connects_thisweek_notion_failure_non_fatal():
    mock_get_user_name.return_value = "Test User"
    mock_notion.get_profile_stats_by_name.side_effect = Exception("Notion API error")
    
    # Should not raise exception
    response = handle_connects_thisweek(ConnectsThisweekRequest(
        result={"value": 3},
        channelName="test-channel"
    ))
    
    # Should still complete successfully
    assert "Коннекти на цьому тижні: 3" in response.output
    assert response.survey == "continue"
    
    # HTTP should still be called
    mock_http.post_connects_to_db.assert_called_once()
    
    # Survey step should still be marked complete
    mock_postgres.upsert_survey_step.assert_called_with(
        ANY, "connects_thisweek", completed=True
    )

def test_connects_thisweek_no_profile_page_continues_normally():
    mock_get_user_name.return_value = "New User"
    mock_notion.get_profile_stats_by_name.return_value = None  # No profile page
    
    response = handle_connects_thisweek(ConnectsThisweekRequest(
        result={"value": 2}
    ))
    
    # Should complete normally
    assert "Коннекти на цьому тижні: 2" in response.output
    
    # HTTP should be called
    mock_http.post_connects_to_db.assert_called_once()
    
    # Notion update should not be attempted
    mock_notion.update_connects.assert_not_called()

def test_connects_thisweek_zero_connects_is_valid():
    with freeze_time("2024-01-15 09:15:00", tz_offset=2):
        response = handle_connects_thisweek(ConnectsThisweekRequest(
            result={"stepName": "connects_thisweek", "value": 0},
            channelName="test-channel"
        ))
        
        assert "Коннекти на цьому тижні: 0" in response.output
        assert response.survey == "continue"
        
        # Should still call HTTP service with 0
        mock_http.post_connects_to_db.assert_called_with(
            name=ANY, connects=0
        )

def test_connects_thisweek_http_failure_propagates_error():
    mock_http.post_connects_to_db.side_effect = Exception("HTTP service unavailable")
    
    with pytest.raises(Exception, match="HTTP service unavailable"):
        handle_connects_thisweek(ConnectsThisweekRequest(
            result={"value": 5}
        ))
```

## 6. Acceptance Criteria

- [ ] **HTTP service call** to `https://tech2.etcetera.kiev.ua/set-db-connects` with `name` and `connects` parameters
- [ ] **Notion update non-fatal** - Profile Stats DB update failure does not break flow
- [ ] **Profile page check** - Only update Notion if profile page exists
- [ ] **Zero connects valid** - `value: 0` is valid input
- [ ] **Survey step completion** upserts `connects_thisweek` with `completed=true`
- [ ] **Response format** matches template exactly including newlines
- [ ] **Time formatting** as HH:MM in response
- [ ] **Channel name** without # prefix in response
- [ ] **Error handling** for HTTP failures (fatal) vs Notion failures (non-fatal)
- [ ] **Coverage ≥ 90%** for connects_thisweek handler module