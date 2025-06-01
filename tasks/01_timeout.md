# Revised Survey Timeout Fix Plan

## Part 1: Fixing Orphaned Views
### 1. Add View Reference to Survey
File: `services/survey.py`
```python
class SurveyFlow:
    def __init__(self, channel_id: str, steps: List[str], user_id: str, session_id: str):
        # Existing properties
        self.active_view: Optional[discord.ui.View] = None  # Add this
```

### 2. Update View Handling
File: `discord_bot/commands/survey.py`
```python
async def ask_dynamic_step(...):
    # After creating view
    survey.active_view = view  # Attach view to survey
```

### 3. Enhance Survey Resumption
File: `discord_bot/commands/survey.py`
```python
async def handle_start_daily_survey(...):
    if existing_survey:
        # Clean up previous view
        if existing_survey.active_view:
            existing_survey.active_view.stop()
        # Resume survey flow
        await ask_dynamic_step(...)
```

### 4. Improve Cleanup
File: `services/survey.py`
```python
class SurveyManager:
    def remove_survey(self, channel_id: str):
        survey = self.surveys.get(channel_id)
        if survey:
            if survey.active_view:
                survey.active_view.stop()
            del self.surveys[channel_id]
```

## Part 2: Add User Timeout Notification
```pseudocode
ADD USER NOTIFICATION:
  MODIFY handle_survey_incomplete():
    AFTER WEBHOOK SEND (line 108):
      TRY:
        SEND MESSAGE: f"<@{survey.user_id}> {Strings.TIMEOUT_MESSAGE}"
      EXCEPT:
        LOG ERROR
```

## Implementation Details

### Timeout Notification
File: `discord_bot/commands/survey.py`
```diff
async def handle_survey_incomplete(...):
    ...
    await webhook_service.send_webhook(...)
    
+   # Notify user about timeout
+   try:
+       await channel.send(f"<@{survey.user_id}> {Strings.TIMEOUT_MESSAGE}")
+   except Exception as e:
+       logger.error(f"Failed to send timeout message: {e}")
+
    survey_manager.remove_survey(...)
    ...
```

## Verification
1. Test timeout scenario
        IF survey EXISTS:
            CALL handle_survey_incomplete()
        ELSE:
            LOG "Orphaned view timeout"
    FINALLY:
        STOP view  // Always stop view
```


## Verification Plan
1. Test survey resumption in same channel
2. Verify timeout after 15 minutes
3. Check view cleanup when new survey starts
4. Monitor for orphaned view warnings

## Benefits
- Maintains channel-bound survey requirement
- Prevents orphaned views
- Ensures proper timeout handling
- Minimal code changes