import discord
from typing import Optional, List
from config import ViewType, logger
from services import survey_manager

class DayOffButton(discord.ui.Button):
    def __init__(self, label: str, custom_id: str):
        super().__init__(
            style=discord.ButtonStyle.primary,
            label=label,
            custom_id=custom_id
        )
        
    async def callback(self, interaction: discord.Interaction):
        from services import webhook_service  # Import here to avoid circular dependency
        await webhook_service.send_button_pressed_info(interaction, self)

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
        custom_id = f"day_off_button_{day}_{cmd_or_step}_{user_id}"
        button = DayOffButton(label=day, custom_id=custom_id)
        view.add_item(button)
    
    return view 