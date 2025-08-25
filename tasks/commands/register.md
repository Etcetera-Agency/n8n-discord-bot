# Register Command Implementation

## 1. What the n8n flow does

### n8n Node Sequence:
1. **Switch** → Routes to "register" branch when `command.startsWith("register")`
2. **Notion search TD** → Searches Team Directory by `Name|title` contains `result.text`
3. **Check register** → Switch node checking if channel already registered:
   - **Public Channel**: Hardcoded channel IDs check
   - **Already**: Regex check for 19-digit Discord channel ID
   - **Extra**: New registration path
4. **Notion add ID, Channel ID** → Updates page with:
   - `Discord ID|rich_text` = `userId`
   - `Discord channel ID|rich_text` = `channelId`
5. **Register** → Set node with success message
6. **Respond Registred** → Returns response

### Branching Logic:
- **Input**: `{ command: "register", result: { text: "User Name" } }`
- **Side Effects**: Updates Notion Team Directory properties
- **Conditions**: 
  - If channel already in public list → "Канал вже зареєстрований на когось іншого"
  - If channel has 19-digit ID → "Канал вже зареєстрований на когось іншого"
  - Else → Update Notion and return success

## 2. Response Templates (exact)

### Success Registration
```
Канал успішно зареєстровано на {{ property_name }}
```

### Already Registered
```
Канал вже зареєстрований на когось іншого.
```

### Examples:
```
Канал успішно зареєстровано на Сергій Шевчик
```

```
Канал вже зареєстрований на когось іншого.
```

## 3. Pseudocode (15 lines)

```python
def handle_register(request):
    user_name = request.result.text
    channel_id = request.channelId
    
    # Search user in Team Directory
    user_pages = notion_client.search_team_directory(name_contains=user_name)
    if not user_pages:
        return {"output": "Користувача не знайдено"}
    
    # Check if channel already registered
    existing = notion_client.search_team_directory(channel_id=channel_id)
    if existing and (channel_id in PUBLIC_CHANNELS or is_registered_channel(existing)):
        return {"output": "Канал вже зареєстрований на когось іншого."}
    
    # Update user page with Discord info
    user_page = user_pages[0]
    notion_client.update_page(user_page.url, {
        "Discord ID|rich_text": request.userId,
        "Discord channel ID|rich_text": channel_id
    })
    
    return {"output": f"Канал успішно зареєстровано на {user_page.name}"}
```

## 4. Request/Response Schema

### Request DTO
```python
@dataclass
class RegisterRequest:
    command: str  # "register"
    result: dict  # {"text": "User Name"}
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
class RegisterResponse:
    output: str
```

**Response Schema**: `{ "output": "string" }`

## 5. Tests (pytest)

### Test Function Names:
- `test_register_success_updates_notion_and_formats_ok()`
- `test_register_user_not_found_returns_error()`
- `test_register_channel_already_in_public_list_returns_already_registered()`
- `test_register_channel_already_has_19_digit_id_returns_already_registered()`
- `test_register_notion_update_failure_propagates_error()`
- `test_register_multiple_users_found_uses_first_match()`

### Key Test Cases:
```python
def test_register_success_updates_notion_and_formats_ok():
    # Mock Notion responses
    mock_notion.search_team_directory.side_effect = [
        [MockPage(name="Сергій Шевчик", url="page-url")],  # User search
        []  # Channel search (not registered)
    ]
    
    response = handle_register(RegisterRequest(
        command="register",
        result={"text": "Сергій"},
        userId="829736729991970838",
        channelId="1362738788505485414"
    ))
    
    assert response.output == "Канал успішно зареєстровано на Сергій Шевчик"
    mock_notion.update_page.assert_called_with("page-url", {
        "Discord ID|rich_text": "829736729991970838",
        "Discord channel ID|rich_text": "1362738788505485414"
    })

def test_register_channel_already_in_public_list_returns_already_registered():
    mock_notion.search_team_directory.return_value = [
        MockPage(name="Сергій Шевчик")
    ]
    
    response = handle_register(RegisterRequest(
        channelId="1362662345737769101"  # Public channel
    ))
    
    assert response.output == "Канал вже зареєстрований на когось іншого."
```

## 6. Acceptance Criteria

- [ ] **Byte-for-byte equivalence** with n8n "Register" Set node output
- [ ] **Notion property updates** use exact keys: `Discord ID|rich_text`, `Discord channel ID|rich_text`
- [ ] **Public channel detection** matches hardcoded list: `['1362662345737769101', '1348253056097189908', '1348274077978202153', '1348273069466189977']`
- [ ] **19-digit channel ID regex** validation: `^\\d{19}$`
- [ ] **User search** by `Name|title` contains logic
- [ ] **Error handling** for Notion API failures
- [ ] **Response format** matches schema: `{"output": "string"}`
- [ ] **Ukrainian text** preserved exactly as in templates
- [ ] **Coverage ≥ 90%** for register handler module