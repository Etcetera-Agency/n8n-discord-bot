import discord
from typing import Optional, List
import datetime
from config import ViewType, logger
from services import survey_manager

class DayOffButton(discord.ui.Button):
    def __init__(self, label: str, custom_id: str, cmd_or_step: str):
        super().__init__(
            style=discord.ButtonStyle.primary,
            label=label,
            custom_id=custom_id
        )
        self.cmd_or_step = cmd_or_step
        
    async def callback(self, interaction: discord.Interaction):
        from services import webhook_service  # Import here to avoid circular dependency
        
        # Extract command type from custom_id
        # Format: day_off_button_{day}_{cmd_or_step}_{user_id}
        if "day_off_thisweek" in self.cmd_or_step or "day_off_nextweek" in self.cmd_or_step:
            # This is a slash command - send the actual command result
            await webhook_service.send_interaction_response(
                interaction,
                initial_message=f"Обробка вибору: {self.label}",
                command=self.cmd_or_step,
                result={"value": self.label}
            )
        elif not any(cmd in self.cmd_or_step for cmd in ["survey", "day_off_thisweek", "day_off_nextweek"]):
            # This is a mention-based interaction - send button_pressed
            await webhook_service.send_webhook(
                interaction,
                command="button_pressed",
                status="ok",
                result={
                    "label": self.label,
                    "custom_id": self.custom_id,
                    "value": self.label
                }
            )
        # For survey steps - don't send anything, handled by survey manager

class DayOffView(discord.ui.View):
    def __init__(self, timeout: Optional[float] = 180):
        super().__init__(timeout=timeout)

def create_day_off_view(
    cmd_or_step: str,
    user_id: str,
    timeout: Optional[float] = None,
    has_survey: bool = False
) -> DayOffView:
    """Create a day off view with buttons."""
    view = DayOffView(timeout=timeout)
    
    # Map of weekday names to their numeric values (0 = Monday, 6 = Sunday)
    weekday_map = {
        "Monday": 0,
        "Tuesday": 1,
        "Wednesday": 2,
        "Thursday": 3,
        "Friday": 4,
        "Saturday": 5,
        "Sunday": 6
    }
    
    # Get current weekday (0 = Monday, 6 = Sunday)
    current_date = datetime.datetime.now()
    current_weekday = current_date.weekday()
    
    # Add day off buttons
    days = [
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday",
        "Saturday",
        "Sunday"
    ]
    
    for day in days:
        # For thisweek command, skip days that have already passed
        if "day_off_thisweek" in cmd_or_step and weekday_map[day] < current_weekday:
            continue
            
        custom_id = f"day_off_button_{day}_{cmd_or_step}_{user_id}"
        button = DayOffButton(label=day, custom_id=custom_id, cmd_or_step=cmd_or_step)
        view.add_item(button)
    
    return view 