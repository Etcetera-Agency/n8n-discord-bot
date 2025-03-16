import discord
from typing import Optional, List
from config import ViewType, logger
from services import survey_manager

class WorkloadButton(discord.ui.Button):
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
        # Format: workload_button_{value}_{cmd_or_step}_{user_id}
        if "workload_today" in self.cmd_or_step or "workload_nextweek" in self.cmd_or_step:
            # This is a slash command - send the actual command result
            value = "0" if self.label == "Нічого немає" else self.label
            await webhook_service.send_webhook(
                interaction,
                command=self.cmd_or_step,
                status="ok",
                result={"value": value}
            )
        elif not any(cmd in self.cmd_or_step for cmd in ["survey", "workload_today", "workload_nextweek"]):
            # This is a mention-based interaction - send button_pressed
            await webhook_service.send_webhook(
                interaction,
                command="button_pressed",
                status="ok",
                result={
                    "label": self.label,
                    "custom_id": self.custom_id,
                    "value": "0" if self.label == "Нічого немає" else self.label
                }
            )
        # For survey steps - don't send anything, handled by survey manager

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
        button = WorkloadButton(label=label, custom_id=custom_id, cmd_or_step=cmd_or_step)
        view.add_item(button)
    
    return view 