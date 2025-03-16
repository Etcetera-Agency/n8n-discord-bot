import discord
from typing import Optional, List
from config import ViewType, logger
from services import survey_manager

class WorkloadButton(discord.ui.Button):
    def __init__(self, label: str, custom_id: str):
        super().__init__(
            style=discord.ButtonStyle.primary,
            label=label,
            custom_id=custom_id
        )
        
    async def callback(self, interaction: discord.Interaction):
        from services import webhook_service  # Import here to avoid circular dependency
        await webhook_service.send_button_pressed_info(interaction, self)

class WorkloadView(discord.ui.View):
    def __init__(self, timeout: Optional[float] = 180):
        super().__init__(timeout=timeout)

def create_workload_view(
    cmd_or_step: str,
    user_id: str,
    timeout: Optional[float] = None,
    has_survey: bool = False
) -> WorkloadView:
    """Create a workload view with buttons."""
    view = WorkloadView(timeout=timeout)
    
    # Add workload buttons
    buttons = [
        ("0", "Нічого немає"),
        ("1-10", "1-10"),
        ("11-20", "11-20"),
        ("21-30", "21-30"),
        ("31-40", "31-40"),
        ("40+", "40+")
    ]
    
    for value, label in buttons:
        custom_id = f"workload_button_{value}_{cmd_or_step}_{user_id}"
        button = WorkloadButton(label=label, custom_id=custom_id)
        view.add_item(button)
    
    return view 