# Mention Command Implementation

## 1. What the n8n flow does

### n8n Node Sequence:
1. **If mention** → Checks if `command == "mention"`
2. **Bot reply** → Set node with mention response template
3. **Respond to Webhook** → Returns response

### Branching Logic:
- **Input**: `{ command: "mention", userId: "829736729991970838" }`
- **Side Effects**: None (read-only operation)
- **Condition**: Direct command match for mention handling

## 2. Response Templates (exact)

### Bot Mention Response
```
Я ще не вмію вільно розмовляти. Використовуй слеш команди <@{userId}>. Почни із /
```

### Examples:
```
Я ще не вмію вільно розмовляти. Використовуй слеш команди <@829736729991970838>. Почни із /
```

```
Я ще не вмію вільно розмовляти. Використовуй слеш команди <@123456789012345678>. Почни із /
```

## 3. Pseudocode (15 lines)

```python
def handle_mention(request):
    user_id = request.userId
    
    return {
        "output": f"Я ще не вмію вільно розмовляти. Використовуй слеш команди <@{user_id}>. Почни із /"
    }
```

## 4. Request/Response Schema

### Request DTO
```python
@dataclass
class MentionRequest:
    command: str  # "mention"
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
class MentionResponse:
    output: str
```

**Response Schema**: `{ "output": "string" }`

## 5. Tests (pytest)

### Test Function Names:
- `test_mention_formats_user_id_correctly()`
- `test_mention_preserves_exact_ukrainian_text()`
- `test_mention_handles_different_user_ids()`
- `test_mention_response_schema_compliance()`

### Key Test Cases:
```python
def test_mention_formats_user_id_correctly():
    response = handle_mention(MentionRequest(
        command="mention",
        userId="829736729991970838",
        channelId="1362738788505485414",
        sessionId="test_session",
        author="test_user",
        channelName="test-channel",
        timestamp=1755687677,
        message="@bot hello"
    ))
    
    expected_output = "Я ще не вмію вільно розмовляти. Використовуй слеш команди <@829736729991970838>. Почни із /"
    assert response.output == expected_output

def test_mention_preserves_exact_ukrainian_text():
    response = handle_mention(MentionRequest(
        userId="123456789012345678"
    ))
    
    # Verify exact Ukrainian text preservation
    assert "Я ще не вмію вільно розмовляти" in response.output
    assert "Використовуй слеш команди" in response.output
    assert "Почни із /" in response.output
    assert "<@123456789012345678>" in response.output

def test_mention_handles_different_user_ids():
    test_user_ids = [
        "829736729991970838",
        "123456789012345678", 
        "999888777666555444"
    ]
    
    for user_id in test_user_ids:
        response = handle_mention(MentionRequest(userId=user_id))
        assert f"<@{user_id}>" in response.output

def test_mention_response_schema_compliance():
    response = handle_mention(MentionRequest(userId="test"))
    
    # Verify response has only 'output' field
    response_dict = response.__dict__
    assert "output" in response_dict
    assert len(response_dict) == 1
    assert isinstance(response.output, str)
```

## 6. Acceptance Criteria

- [ ] **User ID formatting** - Includes `<@{userId}>` in exact format
- [ ] **Ukrainian text preservation** - Exact text from n8n "Bot reply" Set node
- [ ] **Response schema** - Simple `{"output": "string"}` format
- [ ] **No external calls** - Pure string formatting, no API calls
- [ ] **Template compliance** - Byte-for-byte match with n8n output
- [ ] **Coverage ≥ 90%** for mention handler module