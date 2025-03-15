import discord
from typing import Optional
from bot.views.base import BaseView
from config import WORKLOAD_OPTIONS, logger
from services import webhook_service, survey_manager

class WorkloadView(BaseView):
    """View for workload selection buttons."""
    pass

class WorkloadButton(discord.ui.Button):
    """Button for workload selection."""
    def __init__(self, label: str):
        """
        Initialize a workload button.
        
        Args:
            label: Button label
        """
        # Convert "Нічого немає" to "0" for display but keep original for comparison
        display_label = "0" if label == "Нічого немає" else label
        super().__init__(
            style=discord.ButtonStyle.primary,
            label=display_label,
            custom_id=f"workload_button_{label}"
        )
        self.original_label = label  # Store original label for comparison
        
    async def callback(self, interaction: discord.Interaction):
        """Handle button click."""
        await webhook_service.send_button_pressed_info(interaction, self)
        # Convert "Нічого немає" to 0 for value
        value = 0 if self.original_label == "Нічого немає" else int(self.label)
        
        # Get the survey if it exists
        survey = survey_manager.get_survey(str(interaction.user.id))
        if survey:
            survey.add_result(survey.current_step(), value)
            survey.next_step()
            
            # Ask the next question or finish
            if survey.is_done():
                await finish_survey(interaction.channel, survey)
            else:
                next_step = survey.current_step()
                if next_step:
                    await ask_dynamic_step(interaction.channel, survey, next_step)
        
        # Disable all buttons in the view
        for child in self.view.children:
            child.disabled = True
        await interaction.response.edit_message(view=self.view)

def create_workload_view(
    cmd_or_step: str,
    user_id: str,
    timeout: Optional[int] = None,
    has_survey: bool = False
) -> WorkloadView:
    """
    Create a workload view with buttons.
    
    Args:
        cmd_or_step: Command or survey step name
        user_id: Discord user ID
        timeout: View timeout in seconds
        has_survey: Whether this view is part of a survey
        
    Returns:
        A configured WorkloadView instance
    """
    view = WorkloadView(cmd_or_step, user_id, timeout, has_survey)
    for opt in WORKLOAD_OPTIONS:
        view.add_item(WorkloadButton(opt))
    return view 