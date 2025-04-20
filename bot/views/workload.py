import discord
from typing import Optional
from config import logger
from services import survey_manager

class WorkloadView(discord.ui.View):
    """View for workload selection - only used for non-survey commands"""
    def __init__(self, cmd_or_step: str, user_id: str):
        super().__init__(timeout=300)
        self.cmd_or_step = cmd_or_step
        self.user_id = user_id
        
    async def on_timeout(self):
        logger.warning(f"WorkloadView timed out for user {self.user_id}")

class WorkloadButton(discord.ui.Button):
    def __init__(self, hour: str, custom_id: str):
        super().__init__(
            style=discord.ButtonStyle.secondary,
            label=hour,
            custom_id=custom_id
        )

    async def callback(self, interaction: discord.Interaction):
        if not interaction.response.is_done():
            await interaction.response.defer()
        logger.info(f"Workload selected: {self.label}")

def create_workload_view(cmd: str, user_id: str, timeout: Optional[float] = None) -> WorkloadView:
    """Create workload view for regular commands only"""
    view = WorkloadView(cmd, user_id)
    
    from config.constants import WORKLOAD_OPTIONS
    workload_options = [opt for opt in WORKLOAD_OPTIONS if opt != "Нічого немає"]  # Filter out non-numeric option
    for hour in workload_options:
        button = WorkloadButton(
            hour=hour,
            custom_id=f"workload_cmd_{hour}_{user_id}" 
        )
        view.add_item(button)
    
    return view