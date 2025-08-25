# Default/Fallback Command Implementation

## 1. What the n8n flow does

### n8n Node Sequence:
1. **Switch** → Falls through to "extra" fallback when no other conditions match
2. **Respond not Registred** → Returns generic error response

### Branching Logic:
- **Input**: Any command that doesn't match other patterns
- **Side Effects**: None (read-only operation)
- **Condition**: Fallback for unrecognized commands

## 2. Response Templates (exact)

### Generic Error Response
```json
{
  "output": "Some error"
}
```

### Examples:
```json
{
  "output": "Some error"
}
```

## 3. Pseudocode (15 lines)

```python
def handle_default(request):
    return {
        "output": "Some error"
    }
```

## 4. Request/Response Schema

### Request DTO
```python
@dataclass
class DefaultRequest:
    command: str  # Any unrecognized command
    userId: str
    channelId: str
    sessionId: str
    author: str
    channelName: str
    timestamp: int
    message: str
```

### Response DTO
```python
@dataclass
class DefaultResponse:
    output: str
```

**Response Schema**: `{ "output": "string" }`

## 5. Tests (pytest)

### Test Function Names:
- `test_default_returns_generic_error()`
- `test_default_handles_any_command()`
- `test_default_response_schema_compliance()`
- `test_default_no_external_calls()`

### Key Test Cases:
```python
def test_default_returns_generic_error():
    response = handle_default(DefaultRequest(
        command="unknown_command",
        userId="829736729991970838",
        channelId="1362738788505485414",
        sessionId="test_session",
        author="test_user",
        channelName="test-channel",
        timestamp=1755687677,
        message="some unknown message"
    ))
    
    assert response.output == "Some error"

def test_default_handles_any_command():
    test_commands = [
        "invalid_command",
        "random_text",
        "",
        "123",
        "special!@#$%characters"
    ]
    
    for command in test_commands:
        response = handle_default(DefaultRequest(command=command))
        assert response.output == "Some error"

def test_default_response_schema_compliance():
    response = handle_default(DefaultRequest(command="test"))
    
    # Verify response has only 'output' field
    response_dict = response.__dict__
    assert "output" in response_dict
    assert len(response_dict) == 1
    assert isinstance(response.output, str)

def test_default_no_external_calls():
    # Mock all external clients to ensure they're not called
    with patch('clients.notion') as mock_notion, \
         patch('clients.postgres') as mock_postgres, \
         patch('clients.gcal') as mock_gcal, \
         patch('clients.http') as mock_http:
        
        handle_default(DefaultRequest(command="test"))
        
        # Verify no external calls made
        mock_notion.assert_not_called()
        mock_postgres.assert_not_called() 
        mock_gcal.assert_not_called()
        mock_http.assert_not_called()
```

## 6. Acceptance Criteria

- [ ] **Generic error message** - Returns exact "Some error" text from n8n
- [ ] **Fallback behavior** - Handles any unrecognized command
- [ ] **Response schema** - Simple `{"output": "string"}` format
- [ ] **No external calls** - Pure response, no API interactions
- [ ] **Template compliance** - Matches n8n "Respond not Registred" output
- [ ] **Coverage ≥ 90%** for default handler module