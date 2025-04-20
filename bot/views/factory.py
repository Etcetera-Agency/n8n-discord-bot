from typing import Optional, Union
import discord
from config import ViewType, logger, Strings
from bot.views.workload import create_workload_view
from bot.views.day_off import create_day_off_view

class WorkloadTodayModal(discord.ui.Modal):
    def __init__(self, survey, step_name):
        super().__init__(title=Strings.WORKLOAD_TODAY, timeout=120)
        self.survey = survey
        self.step_name = step_name
        self.input = discord.ui.TextInput(
            label=Strings.WORKLOAD_TODAY,
            placeholder=Strings.SELECT_HOURS,
            min_length=1,
            max_length=3
        )
        self.add_item(self.input)

class WorkloadNextWeekModal(discord.ui.Modal):
    def __init__(self, survey, step_name):
        super().__init__(title=Strings.WORKLOAD_NEXTWEEK, timeout=120)
        self.survey = survey
        self.step_name = step_name
        self.input = discord.ui.TextInput(
            label=Strings.WORKLOAD_NEXTWEEK,
            placeholder=Strings.SELECT_HOURS,
            min_length=1,
            max_length=3
        )
        self.add_item(self.input)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer()
        try:
            # Validate input
            if not self.input.value.isdigit():
                await interaction.followup.send(Strings.INVALID_INPUT, ephemeral=True)
                return

            # Store result
            self.survey.add_result(self.step_name, int(self.input.value))
            
            # Cleanup previous message
            if hasattr(self.survey, 'current_step_message'):
                try:
                    msg = await interaction.channel.fetch_message(self.survey.current_step_message)
                    await msg.delete()
                except:
                    logger.warning("Could not delete survey question message")

            # Confirm submission
            await interaction.followup.send(Strings.INPUT_SAVED, ephemeral=True)
            
            # Advance survey
            await self.survey.next_step()
            if not self.survey.is_done():
                from bot.commands.survey import continue_survey
                await continue_survey(interaction.channel, self.survey)
                
        except Exception as e:
            logger.error(f"Error handling workload modal submit: {e}")
            await interaction.followup.send(Strings.GENERAL_ERROR, ephemeral=True)

class DayOffNextWeekModal(discord.ui.Modal):
    def __init__(self, survey, step_name):
        super().__init__(title=Strings.DAY_OFF_NEXTWEEK, timeout=120)
        self.survey = survey
        self.step_name = step_name
        self.input = discord.ui.TextInput(
            label=Strings.DAY_OFF_NEXTWEEK,
            placeholder=Strings.SELECT_DAYS_NEXTWEEK,
            min_length=1,
            max_length=100
        )
        self.add_item(self.input)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer()
        try:
            # Validate input
            if not self.input.value.strip():
                await interaction.followup.send(Strings.INVALID_INPUT, ephemeral=True)
                return

            # Store result
            self.survey.add_result(self.step_name, self.input.value)
            
            # Cleanup previous message
            if hasattr(self.survey, 'current_step_message'):
                try:
                    msg = await interaction.channel.fetch_message(self.survey.current_step_message)
                    await msg.delete()
                except:
                    logger.warning("Could not delete survey question message")

            # Confirm submission
            await interaction.followup.send(Strings.INPUT_SAVED, ephemeral=True)
            
            # Advance survey
            await self.survey.next_step()
            if not self.survey.is_done():
                from bot.commands.survey import continue_survey
                await continue_survey(interaction.channel, self.survey)
                
        except Exception as e:
            logger.error(f"Error handling day off modal submit: {e}")
            await interaction.followup.send(Strings.GENERAL_ERROR, ephemeral=True)

def create_view(
    view_name: str, 
    cmd_or_step: str,
    user_id: str,
    timeout: Optional[float] = None,
    has_survey: bool = False
) -> Union[discord.ui.View, discord.ui.Modal]:
    """
    Factory function to create the appropriate view type.
    
    # Survey view handling (button-based implementation)
    if view_name == "survey":
        from bot.views.generic import create_survey_view
        return create_survey_view(cmd_or_step, user_id, **kwargs)
    
    logger.info(f"Creating {view_name} view for command: {cmd_or_step}")
    
    # Handle modal creation for survey steps
    if has_survey:
        if view_name == "workload_today":
            return WorkloadTodayModal(cmd_or_step, user_id)
        elif view_name == "workload_nextweek":
            return WorkloadNextWeekModal(cmd_or_step, user_id)
        elif view_name == "day_off_nextweek":
            return DayOffNextWeekModal(cmd_or_step, user_id)
    
    # Fall back to button views
    if view_name == "workload":
        return create_workload_view(cmd_or_step, user_id, **kwargs)
    elif view_name == "day_off":
        return create_day_off_view(cmd_or_step, user_id, timeout, has_survey)
    
    # Default empty view
    return discord.ui.View(timeout=timeout)
