# Slash Command Timeout Notification Plan

## Objective
Update original command message with timeout notification when slash command views expire after 15 minutes.

## Implementation Steps

### 1. Store Original Message Reference
```python
# In view __init__ (e.g. WorkloadView_slash, DayOffView_slash)
self.command_msg: discord.Message = None  # Already exists in current implementation
```

### 2. Modify on_timeout() Method
```python
async def on_timeout(self):
    from config import Strings  # Import locally to avoid circular imports
    
    # Existing cleanup
    if self.buttons_msg:
        try:
            await self.buttons_msg.delete()
        except:
            pass
    
    # NEW: Update original command message
    if self.command_msg:
        try:
            # Get first 13 characters of timeout message
            timeout_msg = Strings.TIMEOUT_MESSAGE[:13]  
            
            # Update message content
            await self.command_msg.edit(
                content=f"{self.command_msg.content}\n{timeout_msg}"
            )
        except Exception as e:
            logger.error(f"Failed to update command message on timeout: {e}")
    
    self.stop()
```

### 3. Apply to All Slash Command Views
- Implement in:
  - [`discord_bot/views/workload_slash.py`](discord_bot/views/workload_slash.py)
  - [`discord_bot/views/day_off_slash.py`](discord_bot/views/day_off_slash.py)
  - Any other slash command views

### 4. Verify TIMEOUT_MESSAGE Exists
Confirm in [`config/strings.py`](config/strings.py):
```python
TIMEOUT_MESSAGE = "⏱️ Час очікування минув. Будь ласка, почніть спочатку."
```

## Expected Behavior
When a slash command view times out after 15 minutes:
1. Buttons message is deleted
2. Original command message is updated with:
```
<original content>
⏱️ Час очікув...
```

## Verification Plan
1. Trigger slash command timeout
2. Confirm:
   - Buttons disappear
   - Original message updates with timeout snippet
   - No errors in logs