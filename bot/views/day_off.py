import discord
from typing import Optional, List
import datetime
from bot.views.base import BaseView
from config import WEEKDAY_OPTIONS, logger
from services import webhook_service, survey_manager

class DayOffView(BaseView):
    """View for day off selection."""
    def __init__(
        self,
        cmd_or_step: str,
        user_id: str,
        timeout: Optional[int] = None,
        has_survey: bool = False
    ):
        """
        Initialize the day off view.
        
        Args:
            cmd_or_step: Command or survey step name
            user_id: Discord user ID
            timeout: View timeout in seconds
            has_survey: Whether this view is part of a survey
        """
        super().__init__(cmd_or_step, user_id, timeout, has_survey)
        self.days_selected: List[str] = []

class DayOffSelect(discord.ui.Select):
    """Select menu for choosing days off."""
    def __init__(self, parent_view: DayOffView, filter_passed_days: bool = False):
        """
        Initialize the day off select menu.
        
        Args:
            parent_view: Parent view
            filter_passed_days: Whether to filter out days that have already passed
        """
        # Get available options based on current day if filtering is enabled
        options = WEEKDAY_OPTIONS
        if filter_passed_days:
            # Get current day of week (0 is Monday in our implementation)
            current_date = datetime.datetime.now()
            current_day_idx = current_date.weekday()  # 0 = Monday, 6 = Sunday
            
            # Filter out days that have already passed
            options = [option for i, option in enumerate(WEEKDAY_OPTIONS) if i >= current_day_idx]
            
            # If all days have passed (it's Sunday), show all options
            if not options:
                options = WEEKDAY_OPTIONS
        
        super().__init__(
            placeholder="Оберіть день(і) вихідних",
            min_values=1,
            max_values=7,
            options=options
        )
        self.parent_view = parent_view
    
    async def callback(self, interaction: discord.Interaction) -> None:
        """
        Handle select menu change.
        
        Args:
            interaction: Discord interaction
        """
        await webhook_service.send_button_pressed_info(interaction, self)
        self.parent_view.days_selected = self.values
        await interaction.response.defer()

class DayOffSubmitButton(discord.ui.Button):
    """Button for submitting selected days off."""
    def __init__(self, parent_view: DayOffView):
        """
        Initialize the submit button.
        
        Args:
            parent_view: Parent view
        """
        super().__init__(label="Відправити дні", style=discord.ButtonStyle.primary)
        self.parent_view = parent_view
    
    async def callback(self, interaction: discord.Interaction) -> None:
        """
        Handle button click.
        
        Args:
            interaction: Discord interaction
        """
        await webhook_service.send_button_pressed_info(interaction, self)
        
        if not self.parent_view.days_selected:
            await interaction.response.send_message("Дні не обрано.", ephemeral=False)
            return
        
        if self.parent_view.has_survey:
            # Dynamic survey flow
            survey = survey_manager.get_survey(self.parent_view.user_id)
            if not survey:
                await interaction.response.send_message("Опитування не знайдено.", ephemeral=False)
                return
            
            success, _ = await webhook_service.send_webhook(
                interaction,
                command="survey",
                status="step",
                result={"stepName": self.parent_view.cmd_or_step, "daysSelected": self.parent_view.days_selected}
            )
            
            if not success:
                await interaction.response.send_message("Помилка виклику n8n.", ephemeral=False)
                return
            
            survey.add_result(self.parent_view.cmd_or_step, self.parent_view.days_selected)
            survey.next_step()
            
            from bot.commands.survey import continue_survey
            await continue_survey(interaction.channel, survey)
        else:
            # Regular slash command
            await webhook_service.send_webhook(
                interaction,
                command=self.parent_view.cmd_or_step,
                result={"daysSelected": self.parent_view.days_selected}
            )
        
        self.parent_view.disable_all_items()
        self.parent_view.stop()

def create_day_off_view(
    cmd_or_step: str,
    user_id: str,
    timeout: Optional[int] = None,
    has_survey: bool = False
) -> DayOffView:
    """
    Create a day off view with select menu and submit button.
    
    Args:
        cmd_or_step: Command or survey step name
        user_id: Discord user ID
        timeout: View timeout in seconds
        has_survey: Whether this view is part of a survey
        
    Returns:
        A configured DayOffView instance
    """
    view = DayOffView(cmd_or_step, user_id, timeout, has_survey)
    
    # Only filter passed days for "thisweek" command
    filter_passed_days = "thisweek" in cmd_or_step
    
    view.add_item(DayOffSelect(view, filter_passed_days))
    view.add_item(DayOffSubmitButton(view))
    return view 