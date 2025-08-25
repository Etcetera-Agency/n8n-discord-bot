# Slash Commands Refactor Plan

## Overview
This document outlines the command routing and handler architecture for migrating Discord bot commands from n8n to Python.

## Command Router Architecture

### Main Router (`services/webhook.py`)
```python
class CommandRouter:
    def __init__(self):
        self.handlers = {
            'register': RegisterHandler(),
            'unregister': UnregisterHandler(), 
            'check_channel': CheckChannelHandler(),
            'survey': SurveyHandler(),
            'mention': MentionHandler(),
            # Fallback handler
            'default': DefaultHandler()
        }
    
    def route(self, request: WebhookRequest) -> WebhookResponse:
        command = self.extract_command(request)
        handler = self.handlers.get(command, self.handlers['default'])
        return handler.handle(request)
```

## Command Extraction Logic

### From n8n Switch Node Conditions:
1. **check_channel**: `command.includes("check_channel")`
2. **register**: `command.startsWith("register")`
3. **unregister**: `command.startsWith("unregister")`
4. **survey.end**: `command.includes("survey") && status.includes("end")`
5. **mention**: `command == "mention"`
6. **all good**: `!message.includes("register") && !message.includes("unregister")`

### Python Implementation:
```python
def extract_command(self, request: WebhookRequest) -> str:
    command = request.body.get('command', '')
    status = request.body.get('status', '')
    message = request.body.get('message', '')
    
    if 'check_channel' in command:
        return 'check_channel'
    elif command.startswith('register'):
        return 'register'
    elif command.startswith('unregister'):
        return 'unregister'
    elif 'survey' in command and 'end' in status:
        return 'survey'
    elif command == 'mention':
        return 'mention'
    elif 'register' not in message and 'unregister' not in message:
        return 'survey'  # Default survey handling
    else:
        return 'default'
```

## Handler Base Class

```python
from abc import ABC, abstractmethod

class BaseHandler(ABC):
    @abstractmethod
    def handle(self, request: WebhookRequest) -> WebhookResponse:
        pass
    
    def validate_request(self, request: WebhookRequest) -> None:
        """Common validation logic"""
        if not request.body.get('channelId'):
            raise ValueError("channelId is required")
        if not request.body.get('userId'):
            raise ValueError("userId is required")
```

## Survey Sub-Router

### Survey Step Routing:
```python
class SurveyHandler(BaseHandler):
    def __init__(self):
        self.step_handlers = {
            'workload_today': WorkloadTodayHandler(),
            'workload_nextweek': WorkloadNextweekHandler(),
            'day_off_thisweek': DayOffThisweekHandler(),
            'day_off_nextweek': DayOffNextweekHandler(),
            'connects_thisweek': ConnectsThisweekHandler(),
            'vacation': VacationHandler()
        }
    
    def handle(self, request: WebhookRequest) -> WebhookResponse:
        status = request.body.get('status')
        
        if status == 'end':
            return self.handle_survey_end(request)
        elif status == 'step':
            return self.handle_survey_step(request)
        elif status == 'incomplete':
            return self.handle_survey_continue(request)
        else:
            return self.handle_survey_cancel(request)
```

## Handler Directory Structure

```
handlers/
├── __init__.py
├── base.py                 # BaseHandler abstract class
├── router.py              # CommandRouter main class
├── registration/
│   ├── __init__.py
│   ├── register.py        # RegisterHandler
│   └── unregister.py      # UnregisterHandler
├── survey/
│   ├── __init__.py
│   ├── survey.py          # SurveyHandler (meta-handler)
│   ├── workload_today.py
│   ├── workload_nextweek.py
│   ├── day_off_thisweek.py
│   ├── day_off_nextweek.py
│   ├── connects_thisweek.py
│   └── vacation.py
├── utility/
│   ├── __init__.py
│   ├── check_channel.py   # CheckChannelHandler
│   ├── mention.py         # MentionHandler
│   └── default.py         # DefaultHandler
```

## Response Normalization

### Webhook Response Schema:
```python
@dataclass
class WebhookResponse:
    status_code: int = 200
    headers: Dict[str, str] = field(default_factory=dict)
    body: Dict[str, Any] = field(default_factory=dict)
    
    def to_json(self) -> str:
        return json.dumps(self.body, ensure_ascii=False)
```

### Response Format Rules:
1. **Non-survey commands**: `{"output": "string"}`
2. **Survey commands**: `{"output": "string", "survey": "continue|end|cancel"}`
3. **Survey end**: `{"output": "string", "survey": "end", "url": "string"}`
4. **Check channel**: `{"output": "string", "steps": ["string"]}`

## Error Handling Strategy

### Handler Error Wrapper:
```python
def safe_handle(self, request: WebhookRequest) -> WebhookResponse:
    try:
        return self.handle(request)
    except ValidationError as e:
        return WebhookResponse(
            status_code=400,
            body={"output": f"Validation error: {e}"}
        )
    except NotionAPIError as e:
        return WebhookResponse(
            status_code=500,
            body={"output": "Спробуй трохи піздніше. Я тут пораюсь по хаті."}
        )
    except Exception as e:
        logger.exception("Unexpected error in handler")
        return WebhookResponse(
            status_code=500,
            body={"output": "Some error"}
        )
```

## Implementation Tasks

### Phase 1: Core Infrastructure
- [ ] Implement `BaseHandler` abstract class
- [ ] Create `CommandRouter` with extraction logic
- [ ] Set up handler directory structure
- [ ] Implement `WebhookResponse` normalization

### Phase 2: Handler Implementation
- [ ] Implement registration handlers (`register`, `unregister`)
- [ ] Implement utility handlers (`check_channel`, `mention`, `default`)
- [ ] Implement survey meta-handler with sub-routing
- [ ] Implement all survey step handlers

### Phase 3: Integration & Testing
- [ ] Set up dependency injection for clients
- [ ] Implement error handling and logging
- [ ] Create handler factory for testing
- [ ] Write integration tests for full request flow