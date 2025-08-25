# Survey Meta-Handler Command Implementation

## 1. What the n8n flow does

### n8n Node Sequence:
1. **Switch** → Routes to "survey.end" branch when `command.includes("survey") && status.includes("end")`
2. **set todourl** → Extracts `property_to_do.trim()` from user data
3. **Respond todourl** → Returns response with URL

### Branching Logic:
- **Input**: `{ command: "survey", status: "end", result: {...} }`
- **Side Effects**: None (read-only operation)
- **Algorithm**: Deterministic parser for survey flow states:
  - `status: "incomplete"` → Continue survey
  - `status: "step"` → Process specific step, continue
  - `status: "end"` → End survey, include user's to-do URL

## 2. Response Templates (exact)

### Survey Continue Template
```json
{
  "output": "Дякую! Продовжуємо опитування.",
  "survey": "continue"
}
```

### Survey End Template
```json
{
  "output": "Дякую! Опитування завершено.",
  "survey": "end",
  "url": "https://notion.so/user-todo-page"
}
```

### Survey Cancel Template
```json
{
  "output": "Опитування скасовано.",
  "survey": "cancel"
}
```

### Examples:
```json
{
  "output": "Дякую! Продовжуємо опитування.",
  "survey": "continue"
}
```

```json
{
  "output": "Дякую! Опитування завершено.",
  "survey": "end",
  "url": "https://www.notion.so/etcetera/Task-123456789"
}
```

## 3. Pseudocode (15 lines)

```python
def handle_survey(request):
    status = request.status
    
    if status == "end":
        # Get user's to-do URL
        user_data = get_user_data_from_channel(request.channelId)
        todo_url = user_data.property_to_do.strip() if user_data else ""
        
        return {
            "output": "Дякую! Опитування завершено.",
            "survey": "end",
            "url": todo_url
        }
    
    elif status == "step":
        # Process specific step via step handlers
        step_name = request.result.stepName
        return route_to_step_handler(step_name, request)
    
    elif status == "incomplete":
        return {
            "output": "Дякую! Продовжуємо опитування.",
            "survey": "continue"
        }
    
    else:
        return {
            "output": "Опитування скасовано.",
            "survey": "cancel"
        }
```

## 4. Request/Response Schema

### Request DTO
```python
@dataclass
class SurveyRequest:
    command: str  # "survey"
    status: str   # "incomplete" | "step" | "end" | "cancel"
    result: dict  # Varies by status
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
class SurveyResponse:
    output: str
    survey: str  # "continue" | "end" | "cancel"
    url: Optional[str] = None  # Only for "end" status
```

**Response Schema**: 
- Continue: `{ "output": "string", "survey": "continue" }`
- End: `{ "output": "string", "survey": "end", "url": "string" }`
- Cancel: `{ "output": "string", "survey": "cancel" }`

## 5. Tests (pytest)

### Test Function Names:
- `test_survey_end_includes_user_todo_url()`
- `test_survey_step_routes_to_appropriate_handler()`
- `test_survey_incomplete_returns_continue()`
- `test_survey_cancel_returns_cancel_response()`
- `test_survey_end_with_empty_todo_url()`
- `test_survey_step_routing_all_step_types()`
- `test_survey_invalid_status_returns_cancel()`

### Key Test Cases:
```python
def test_survey_end_includes_user_todo_url():
    mock_get_user_data.return_value = MockUserData(
        property_to_do="  https://www.notion.so/etcetera/Task-123456789  "
    )
    
    response = handle_survey(SurveyRequest(
        command="survey",
        status="end",
        result={},
        channelId="1362738788505485414"
    ))
    
    assert response.output == "Дякую! Опитування завершено."
    assert response.survey == "end"
    assert response.url == "https://www.notion.so/etcetera/Task-123456789"

def test_survey_step_routes_to_appropriate_handler():
    # Mock step handlers
    mock_workload_handler = Mock(return_value={"output": "Workload recorded", "survey": "continue"})
    mock_step_handlers = {
        "workload_today": mock_workload_handler
    }
    
    with patch('survey_handler.STEP_HANDLERS', mock_step_handlers):
        response = handle_survey(SurveyRequest(
            command="survey",
            status="step",
            result={"stepName": "workload_today", "value": 8}
        ))
    
    assert response.output == "Workload recorded"
    assert response.survey == "continue"
    mock_workload_handler.assert_called_once()

def test_survey_incomplete_returns_continue():
    response = handle_survey(SurveyRequest(
        command="survey",
        status="incomplete",
        result={}
    ))
    
    assert response.output == "Дякую! Продовжуємо опитування."
    assert response.survey == "continue"
    assert response.url is None

def test_survey_end_with_empty_todo_url():
    mock_get_user_data.return_value = MockUserData(property_to_do="")
    
    response = handle_survey(SurveyRequest(
        command="survey",
        status="end",
        result={}
    ))
    
    assert response.survey == "end"
    assert response.url == ""

def test_survey_step_routing_all_step_types():
    step_types = [
        "workload_today",
        "workload_nextweek", 
        "day_off_thisweek",
        "day_off_nextweek",
        "connects_thisweek"
    ]
    
    for step_type in step_types:
        with patch(f'handlers.{step_type}.handle_{step_type}') as mock_handler:
            mock_handler.return_value = {"output": "Test", "survey": "continue"}
            
            response = handle_survey(SurveyRequest(
                status="step",
                result={"stepName": step_type}
            ))
            
            mock_handler.assert_called_once()
            assert response.survey == "continue"

def test_survey_invalid_status_returns_cancel():
    response = handle_survey(SurveyRequest(
        command="survey",
        status="invalid_status",
        result={}
    ))
    
    assert response.output == "Опитування скасовано."
    assert response.survey == "cancel"
```

## 6. Acceptance Criteria

- [ ] **Deterministic routing** - No LLM, pure code-path based on status
- [ ] **Step handler routing** - Delegates to appropriate step handler based on `stepName`
- [ ] **URL extraction** - Trims whitespace from `property_to_do` field
- [ ] **Response schema compliance** - Includes `url` field only for "end" status
- [ ] **Status handling** - Supports "incomplete", "step", "end", "cancel" statuses
- [ ] **Ukrainian responses** - Exact text matching templates
- [ ] **Error handling** - Invalid status defaults to "cancel"
- [ ] **Step handler integration** - Properly calls and returns results from step handlers
- [ ] **Coverage ≥ 90%** for survey meta-handler module