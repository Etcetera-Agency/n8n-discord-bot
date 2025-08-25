# Unregister Command Implementation

## 1. What the n8n flow does

### n8n Node Sequence:
1. **Switch** → Routes to "unregister" branch when `command.startsWith("unregister")`
2. **Notion search TD1** → Searches Team Directory by `Discord channel ID|rich_text` contains `channelId`
3. **If** → Checks if user record exists (`$json.id` exists)
4. **Notion add ID, Channel ID1** → Updates page with:
   - `Discord ID|rich_text` = `userId`
   - `Discord channel ID|rich_text` = `""` (empty string)
5. **already NOT registered1** → Set node with success message
6. **already NOT registered** → Set node for not found case
7. **Respond Registred1** → Returns response

### Branching Logic:
- **Input**: `{ command: "unregister", channelId: "..." }`
- **Side Effects**: Clears `Discord channel ID|rich_text` property
- **Conditions**:
  - If user record found → Clear channel ID and return success
  - If no record found → Return "not registered" message

## 2. Response Templates (exact)

### Unregister Success
```
Готово. Тепер цей канал не зареєстрований ні на кого.
```

### Channel Not Registered
```
Вибачте, але цей канал не зареєстрований ні на кого. Тому не можу зняти його з реєстрації
```

### Examples:
```
Готово. Тепер цей канал не зареєстрований ні на кого.
```

```
Вибачте, але цей канал не зареєстрований ні на кого. Тому не можу зняти його з реєстрації
```

## 3. Pseudocode (15 lines)

```python
def handle_unregister(request):
    channel_id = request.channelId
    user_id = request.userId
    
    # Search for existing registration
    existing_pages = notion_client.search_team_directory(
        channel_id_contains=channel_id
    )
    
    if not existing_pages:
        return {"output": "Вибачте, але цей канал не зареєстрований ні на кого. Тому не можу зняти його з реєстрації"}
    
    # Clear channel registration
    user_page = existing_pages[0]
    notion_client.update_page(user_page.url, {
        "Discord ID|rich_text": user_id,
        "Discord channel ID|rich_text": ""
    })
    
    return {"output": "Готово. Тепер цей канал не зареєстрований ні на кого."}
```

## 4. Request/Response Schema

### Request DTO
```python
@dataclass
class UnregisterRequest:
    command: str  # "unregister"
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
class UnregisterResponse:
    output: str
```

**Response Schema**: `{ "output": "string" }`

## 5. Tests (pytest)

### Test Function Names:
- `test_unregister_success_clears_channel_and_returns_success()`
- `test_unregister_not_registered_returns_expected_message()`
- `test_unregister_notion_search_failure_propagates_error()`
- `test_unregister_notion_update_failure_propagates_error()`
- `test_unregister_multiple_registrations_uses_first_match()`
- `test_unregister_preserves_user_id_in_update()`

### Key Test Cases:
```python
def test_unregister_success_clears_channel_and_returns_success():
    # Mock existing registration
    mock_notion.search_team_directory.return_value = [
        MockPage(url="page-url", id="existing-id")
    ]
    
    response = handle_unregister(UnregisterRequest(
        command="unregister",
        userId="829736729991970838",
        channelId="1362738788505485414"
    ))
    
    assert response.output == "Готово. Тепер цей канал не зареєстрований ні на кого."
    mock_notion.update_page.assert_called_with("page-url", {
        "Discord ID|rich_text": "829736729991970838",
        "Discord channel ID|rich_text": ""
    })

def test_unregister_not_registered_returns_expected_message():
    # Mock no existing registration
    mock_notion.search_team_directory.return_value = []
    
    response = handle_unregister(UnregisterRequest(
        channelId="1362738788505485414"
    ))
    
    assert response.output == "Вибачте, але цей канал не зареєстрований ні на кого. Тому не можу зняти його з реєстрації"
    mock_notion.update_page.assert_not_called()

def test_unregister_preserves_user_id_in_update():
    mock_notion.search_team_directory.return_value = [MockPage(url="page-url")]
    
    handle_unregister(UnregisterRequest(
        userId="test-user-123",
        channelId="test-channel"
    ))
    
    # Verify user ID is preserved during unregistration
    call_args = mock_notion.update_page.call_args[0][1]
    assert call_args["Discord ID|rich_text"] == "test-user-123"
    assert call_args["Discord channel ID|rich_text"] == ""
```

## 6. Acceptance Criteria

- [ ] **Byte-for-byte equivalence** with n8n "already NOT registered1" and "already NOT registered" Set node outputs
- [ ] **Notion property updates** use exact keys: `Discord ID|rich_text`, `Discord channel ID|rich_text`
- [ ] **Channel ID clearing** sets empty string `""` not null
- [ ] **User ID preservation** maintains userId in Discord ID field during unregistration
- [ ] **Search logic** uses `Discord channel ID|rich_text` contains filter
- [ ] **Error handling** for Notion API failures
- [ ] **Response format** matches schema: `{"output": "string"}`
- [ ] **Ukrainian text** preserved exactly as in templates
- [ ] **Coverage ≥ 90%** for unregister handler module