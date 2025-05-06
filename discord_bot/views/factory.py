from typing import Optional, Union
import discord
from config import ViewType, logger, Strings
from .workload_slash import create_workload_view # Use slash-specific workload view
from .day_off_slash import create_day_off_view # Use slash-specific day_off view
from .base import BaseView # Import from original base
from .generic import GenericSelect # Import from original generic

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
                await interaction.followup.send(Strings.INVALID_INPUT, ephemeral=False)
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

            # Send webhook to n8n and show response
            from services import webhook_service
            step_payload = {
                "command": "survey",
                "status": "step",
                "message": "",
                "result": {
                    "stepName": self.step_name,
                    "value": str(self.input.value)
                },
                "userId": str(self.survey.user_id),
                "channelId": str(self.survey.channel_id),
                "sessionId": str(getattr(self.survey, 'session_id', ''))
            }
            success, response = await webhook_service.send_webhook_with_retry(
                interaction.channel,
                step_payload,
                {}
            )
            if response:
                await interaction.followup.send(str(response), ephemeral=False)

            # Advance survey
            await self.survey.next_step()
            if not self.survey.is_done():
                from bot.commands.survey import continue_survey
                await continue_survey(interaction.channel, self.survey)
                
        except Exception as e:
            logger.error(f"Error handling workload modal submit: {e}")
            await interaction.followup.send(Strings.GENERAL_ERROR, ephemeral=False)

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
                await interaction.followup.send(Strings.INVALID_INPUT, ephemeral=False)
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

            # Send webhook to n8n and show response
            from services import webhook_service
            step_payload = {
                "command": "survey",
                "status": "step",
                "message": "",
                "result": {
                    "stepName": self.step_name,
                    "value": str(self.input.value)
                },
                "userId": str(self.survey.user_id),
                "channelId": str(self.survey.channel_id),
                "sessionId": str(getattr(self.survey, 'session_id', ''))
            }
            success, response = await webhook_service.send_webhook_with_retry(
                interaction.channel,
                step_payload,
                {}
            )
            if response:
                await interaction.followup.send(str(response), ephemeral=False)

            # Advance survey
            await self.survey.next_step()
            if not self.survey.is_done():
                from bot.commands.survey import continue_survey
                await continue_survey(interaction.channel, self.survey)
                
        except Exception as e:
            logger.error(f"Error handling day off modal submit: {e}")
            await interaction.followup.send(Strings.GENERAL_ERROR, ephemeral=False)

def create_view(
    view_name: str, 
    cmd_or_step: str,
    user_id: str,
    timeout: Optional[float] = None,
    has_survey: bool = False
) -> Union[discord.ui.View, discord.ui.Modal]:
    """
    Factory function to create the appropriate view type.
    """
    
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
        elif view_name == "connects_thisweek":
             from .connects_survey import ConnectsModal
             # Assuming continue_survey_func is available in the scope where create_view is called
             # and passed down. If not, you might need to adjust how this function is called.
             return ConnectsModal(cmd_or_step, user_id, continue_survey_func)

    # Handle connects_thisweek slash command case explicitly
    if cmd_or_step == "connects_thisweek" and not has_survey:
        logger.debug(f"[{user_id}] - create_view called for connects_thisweek slash command. Returning None as no view is needed.")
        return None # No view needed for this slash command

    # Fall back to button views
    if cmd_or_step in ["workload_today", "workload_nextweek"]:
        logger.debug(f"[{user_id}] - Attempting to create workload view for: {cmd_or_step} with has_survey={has_survey}")
        try:
            view = create_workload_view(cmd_or_step, user_id, has_survey=has_survey, continue_survey_func=continue_survey_func)
            logger.debug(f"[{user_id}] - Successfully created workload view for: {cmd_or_step}")
            return view
        except Exception as e:
            logger.error(f"[{user_id}] - Error creating workload view for {cmd_or_step}: {e}", exc_info=True)
            # Return an empty view or None to indicate failure, depending on expected behavior
            return discord.ui.View(timeout=timeout) # Return empty view on error
    elif view_name == "day_off": # Keep existing day_off check
        logger.debug(f"Creating day_off view for {cmd_or_step}, user {user_id}")
        try:
            view = create_day_off_view(cmd_or_step, user_id, timeout, has_survey)
            logger.debug(f"Successfully created day_off view")
            return view
        except Exception as e:
            logger.error(f"Error creating day_off view: {e}")
            raise
    # Default empty view
    return discord.ui.View(timeout=timeout)
