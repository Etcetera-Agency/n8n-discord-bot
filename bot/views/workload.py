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
    def __init__(self, label: str, parent_view: WorkloadView):
        """
        Initialize a workload button.
        
        Args:
            label: Button label
            parent_view: Parent view
        """
        # Convert "Нічого немає" to "0" for display but keep original for comparison
        display_label = "0" if label == "Нічого немає" else label
        super().__init__(
            style=discord.ButtonStyle.primary,
            label=display_label,
            custom_id=f"workload_button_{label}"
        )
        self.original_label = label  # Store original label for comparison
        self.parent_view = parent_view
        
    async def callback(self, interaction: discord.Interaction):
        """Handle button click."""
        await webhook_service.send_button_pressed_info(interaction, self)
        # Convert "Нічого немає" to 0 for value
        value = 0 if self.original_label == "Нічого немає" else int(self.label)
        
        if self.parent_view.has_survey:
            # Dynamic survey flow handling
            survey = survey_manager.get_survey(self.parent_view.user_id)
            if not survey:
                await interaction.response.send_message("Опитування не знайдено.", ephemeral=False)
                return
                
            success, _ = await webhook_service.send_webhook(
                interaction,
                command="survey",
                status="step",
                result={"stepName": self.parent_view.cmd_or_step, "value": value}
            )
            
            if not success:
                await interaction.response.send_message("Помилка виклику n8n.", ephemeral=False)
                return
            
            survey.add_result(self.parent_view.cmd_or_step, value)
            survey.next_step()
            
            from bot.commands.survey import continue_survey
            await continue_survey(interaction.channel, survey)
        else:
            # Regular slash command
            await webhook_service.send_webhook(
                interaction,
                command=self.parent_view.cmd_or_step,
                result={"hours": value}
            )
        
        # Disable all buttons in the view
        self.parent_view.disable_all_items()
        await interaction.response.edit_message(view=self.parent_view)

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
        view.add_item(WorkloadButton(opt, view))
    return view 