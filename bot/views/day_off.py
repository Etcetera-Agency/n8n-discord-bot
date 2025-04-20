import discord
from typing import Optional, List
import datetime
from config import ViewType, logger, constants
from services import survey_manager
import asyncio

class DayOffButton(discord.ui.Button):
    def __init__(self, *, label: str, custom_id: str, cmd_or_step: str):
        super().__init__(
            style=discord.ButtonStyle.secondary,  # Start with gray color
            label=label,
            custom_id=custom_id
        )
        self.cmd_or_step = cmd_or_step
        self.is_selected = False
        
    async def callback(self, interaction: discord.Interaction):
        # First, acknowledge the interaction to prevent timeout
        logger.debug(f"[{interaction.user.id}] - Attempting to defer interaction response for DayOffButton")
        if not interaction.response.is_done():
            await interaction.response.defer(ephemeral=False)
        logger.debug(f"[{interaction.user.id}] - Interaction response deferred for DayOffButton")
        
        # Get the original message
        message = interaction.message
        if message:
            # Add processing reaction
            logger.debug(f"[{interaction.user.id}] - Attempting to add processing reaction to message {message.id}")
            await message.add_reaction(Strings.PROCESSING)
            logger.debug(f"[{interaction.user.id}] - Added processing reaction to message {message.id}")
            
        try:
            # Toggle selection
            self.is_selected = not self.is_selected
            self.style = discord.ButtonStyle.primary if self.is_selected else discord.ButtonStyle.secondary
            
            # Get parent view and update selected days
            view = self.view
            if isinstance(view, DayOffView):
                if self.is_selected:
                    if self.label not in view.selected_days:
                        view.selected_days.append(self.label)
                else:
                    if self.label in view.selected_days:
                        view.selected_days.remove(self.label)
            
            # Update the message with the new button states
            logger.debug(f"[{interaction.user.id}] - Attempting to edit message {interaction.message.id} with updated view")
            await interaction.message.edit(view=self.view)
            logger.debug(f"[{interaction.user.id}] - Message {interaction.message.id} edited with updated view")
            
            # Show success reaction for survey steps
            if message:
                logger.debug(f"[{interaction.user.id}] - Attempting to remove processing reaction from message {message.id}")
                await message.remove_reaction(Strings.PROCESSING, interaction.client.user)
                logger.debug(f"[{interaction.user.id}] - Removed processing reaction from message {message.id}")
                
        except Exception as e:
            logger.error(f"Error in day off button callback: {e}")
            logger.debug(f"Error details - custom_id: {self.custom_id}, interaction: {interaction.data if interaction else None}")
            if message:
                await message.add_reaction("Strings.ERROR")
                await message.remove_reaction(Strings.PROCESSING, interaction.client.user)
                error_msg = Strings.DAYOFF_ERROR.format(
                    days=self.label,
                    error=Strings.UNEXPECTED_ERROR
                )
                await message.edit(content=error_msg)
                await message.add_reaction(Strings.ERROR)

class ConfirmButton(discord.ui.Button):
    def __init__(self):
        super().__init__(
            style=discord.ButtonStyle.success,
            label="Підтверджую",
            row=4  # Put in the last row
        )
        
    async def callback(self, interaction: discord.Interaction):
        from services import webhook_service
        view = self.view
        if isinstance(view, DayOffView):
            # First, acknowledge the interaction to prevent timeout
            logger.debug(f"[{interaction.user.id}] - Attempting to defer interaction response for ConfirmButton")
            if not interaction.response.is_done():
                await interaction.response.defer(ephemeral=False)
            logger.debug(f"[{interaction.user.id}] - Interaction response deferred for ConfirmButton")
            
            # Add processing reaction to command message
            if view.command_msg:
                logger.debug(f"[{interaction.user.id}] - Attempting to add processing reaction to command message {view.command_msg.id}")
                await view.command_msg.add_reaction(Strings.PROCESSING)
                logger.debug(f"[{interaction.user.id}] - Added processing reaction to command message {view.command_msg.id}")
            
            try:
                # Convert selected days to dates
                dates = []
                for day in sorted(view.selected_days, key=lambda x: view.weekday_map[x]):
                    date = view.get_date_for_day(day)
                    if date:
                        dates.append(date)
                
                if view.has_survey:
                    # Dynamic survey flow
                    state = survey_manager.get_survey(view.user_id)
                    if not state:
                        if view.command_msg:
                            await view.command_msg.remove_reaction(Strings.PROCESSING, interaction.client.user)
                            error_msg = Strings.DAYOFF_ERROR.format(
                                days="Підтвердження вихідних",
                                error=Strings.NOT_YOUR_SURVEY
                            )
                            await view.command_msg.edit(content=error_msg)
                            await view.command_msg.add_reaction(Strings.ERROR)
                        if view.buttons_msg:
                            await view.buttons_msg.delete()
                        return
                    
                    # Send webhook for survey step
                    logger.debug(f"[{interaction.user.id}] - Attempting to send webhook for survey step (ConfirmButton): {view.cmd_or_step}")
                    success, data = await webhook_service.send_webhook(
                        interaction,
                        command="survey",
                        status="step",
                        result={
                            "stepName": view.cmd_or_step,
                            "daysSelected": dates
                        }
                    )
                    logger.debug(f"[{interaction.user.id}] - Webhook response for survey step (ConfirmButton): success={success}, data={data}")
                    
                    if not success:
                        if view.command_msg:
                            await view.command_msg.remove_reaction(Strings.PROCESSING, interaction.client.user)
                            error_msg = Strings.DAYOFF_ERROR.format(
                                days=', '.join(dates),
                                error=Strings.GENERAL_ERROR
                            )
                            await view.command_msg.edit(content=error_msg)
                            await view.command_msg.add_reaction(Strings.ERROR)
                        if view.buttons_msg:
                            await view.buttons_msg.delete()
                        return
                    
                    # Update survey state
                    state.results[view.cmd_or_step] = dates
                    state.next_step()
                    next_step = state.current_step()
                    
                    # Update command message with success
                    if view.command_msg:
                        logger.debug(f"[{interaction.user.id}] - Attempting to remove processing reaction from command message {view.command_msg.id}")
                        await view.command_msg.remove_reaction(Strings.PROCESSING, interaction.client.user)
                        logger.debug(f"[{interaction.user.id}] - Attempting to edit command message {view.command_msg.id} with success message")
                        await view.command_msg.edit(content=f"Дякую! Вихідні: {', '.join(dates)} записані.")
                    
                    # Delete buttons message
                    if view.buttons_msg:
                        logger.debug(f"[{interaction.user.id}] - Attempting to delete buttons message {view.buttons_msg.id}")
                        await view.buttons_msg.delete()
                        logger.debug(f"[{interaction.user.id}] - Deleted buttons message {view.buttons_msg.id}")
                    
                    # Continue survey
                    if next_step:
                        from bot.commands.survey import ask_dynamic_step
                        await ask_dynamic_step(interaction.channel, state, next_step)
                    else:
                        from bot.commands.survey import finish_survey
                        await finish_survey(interaction.channel, state)
                        
                else:
                    # Regular slash command
                    # Format dates for n8n (YYYY-MM-DD) in Kyiv time
                    formatted_dates = [
                        view.get_date_for_day(day).strftime("%Y-%m-%d")
                        for day in sorted(view.selected_days, key=lambda x: view.weekday_map[x])
                        if view.get_date_for_day(day) is not None
                    ]
                    
                    logger.debug(f"[{interaction.user.id}] - Attempting to send webhook for regular command (ConfirmButton): {view.cmd_or_step}")
                    success, data = await webhook_service.send_webhook(
                         interaction,
                         command=view.cmd_or_step,
                         status="ok",
                         result={"value": formatted_dates}
                     )
                    logger.debug(f"[{interaction.user.id}] - Webhook response for regular command (ConfirmButton): success={success}, data={data}")
                     
                    if success and data and "output" in data:
                        # Update command message with success
                        if view.command_msg:
                            logger.debug(f"[{interaction.user.id}] - Attempting to remove processing reaction from command message {view.command_msg.id}")
                            await view.command_msg.remove_reaction(Strings.PROCESSING, interaction.client.user)
                            logger.debug(f"[{interaction.user.id}] - Attempting to edit command message {view.command_msg.id} with output: {data['output']}")
                            await view.command_msg.edit(content=data["output"])
                        
                        # Delete buttons message
                        if view.buttons_msg:
                            logger.debug(f"[{interaction.user.id}] - Attempting to delete buttons message {view.buttons_msg.id}")
                            await view.buttons_msg.delete()
                            logger.debug(f"[{interaction.user.id}] - Deleted buttons message {view.buttons_msg.id}")
                    else:
                        if view.command_msg:
                            await view.command_msg.remove_reaction(Strings.PROCESSING, interaction.client.user)
                            await view.command_msg.remove_reaction(Strings.PROCESSING, interaction.client.user)
                            error_msg = Strings.DAYOFF_ERROR.format(
                                days=', '.join(dates),
                                error=Strings.GENERAL_ERROR
                            )
                            await view.command_msg.edit(content=error_msg)
                            await view.command_msg.add_reaction(Strings.ERROR)
                        if view.buttons_msg:
                            await view.buttons_msg.delete()
                        
            except Exception as e:
                logger.error(f"Error in confirm button: {e}")
                if view.command_msg:
                    if view.command_msg:
                        await view.command_msg.remove_reaction(Strings.PROCESSING, interaction.client.user)
                    error_msg = Strings.DAYOFF_ERROR.format(
                        days=', '.join(view.selected_days),
                        error=Strings.UNEXPECTED_ERROR
                    )
                    await view.command_msg.edit(content=error_msg)
                    await view.command_msg.add_reaction(Strings.ERROR)
                if view.buttons_msg:
                    await view.buttons_msg.delete()

class DeclineButton(discord.ui.Button):
    def __init__(self):
        super().__init__(
            style=discord.ButtonStyle.danger,
            label="Не беру",
            row=4  # Put in the last row
        )
        
    async def callback(self, interaction: discord.Interaction):
        from services import webhook_service
        view = self.view
        if isinstance(view, DayOffView):
            logger.info(f"DECLINE BUTTON STARTED - User: {interaction.user}, Command: {view.cmd_or_step}")
            logger.debug(f"Decline button clicked by {interaction.user}")
            logger.debug(f"View has_survey: {view.has_survey}, cmd_or_step: {view.cmd_or_step}")
            
            # Immediately respond to interaction
            try:
                logger.debug(f"[{interaction.user.id}] - Attempting to defer interaction response for DeclineButton")
                await interaction.response.defer(ephemeral=False, thinking=True)
                logger.debug(f"[{interaction.user.id}] - Interaction deferred with thinking state for DeclineButton")
            except Exception as e:
                logger.error(f"Failed to defer interaction: {e}")
                return
            
            # Add processing reaction to command message
            if view.command_msg:
                logger.debug(f"[{interaction.user.id}] - Attempting to add processing reaction to command message {view.command_msg.id}")
                await view.command_msg.add_reaction(Strings.PROCESSING)
                logger.debug(f"[{interaction.user.id}] - Added processing reaction to command message {view.command_msg.id}")
            else:
                logger.debug(f"[{interaction.user.id}] - No command_msg available")
            
            try:
                # Verify webhook service configuration
                logger.debug(f"Preparing to send webhook for decline action")
                logger.debug(f"Webhook service initialized: {'yes' if webhook_service.url else 'no'}")
                logger.debug(f"Webhook URL: {webhook_service.url if webhook_service.url else 'NOT CONFIGURED'}")
                logger.debug(f"Auth token: {'set' if webhook_service.auth_token else 'not set'}")
                
                if view.has_survey:
                    logger.debug("Handling decline action as survey step")
                    state = survey_manager.get_survey(view.user_id)
                    logger.debug(f"Survey state: {'exists' if state else 'not found'}")
                    if not state:
                        if view.command_msg:
                            await view.command_msg.remove_reaction(Strings.PROCESSING, interaction.client.user)
                            error_msg = Strings.DAYOFF_ERROR.format(
                                days="Відмова від вихідних",
                                error=Strings.NOT_YOUR_SURVEY
                            )
                            await view.command_msg.edit(content=error_msg)
                            await view.command_msg.add_reaction(Strings.ERROR)
                        if view.buttons_msg:
                            await view.buttons_msg.delete()
                        return
                    
                    # Send webhook for survey step
                    logger.debug(f"[{interaction.user.id}] - Attempting to send webhook for survey step (DeclineButton): {view.cmd_or_step}")
                    success, data = await webhook_service.send_webhook(
                        interaction,
                        command="survey",
                        status="step",
                        result={
                            "stepName": view.cmd_or_step,
                            "daysSelected": ["Nothing"]  # Keep as "Nothing" for backward compatibility
                        }
                    )
                    logger.debug(f"[{interaction.user.id}] - Webhook response for survey step (DeclineButton): success={success}, data={data}")
                    
                    if not success:
                        if view.command_msg:
                            await view.command_msg.remove_reaction(Strings.PROCESSING, interaction.client.user)
                            error_msg = Strings.DAYOFF_ERROR.format(
                                days="Відмова від вихідних",
                                error=Strings.GENERAL_ERROR
                            )
                            await view.command_msg.edit(content=error_msg)
                            await view.command_msg.add_reaction(Strings.ERROR)
                        if view.buttons_msg:
                            await view.buttons_msg.delete()
                        return
                    
                    # Update survey state
                    state.results[view.cmd_or_step] = ["Nothing"]  # Keep as "Nothing" for backward compatibility
                    state.next_step()
                    next_step = state.current_step()
                    
                    # Update command message with success
                    if view.command_msg:
                        logger.debug(f"[{interaction.user.id}] - Attempting to remove processing reaction from command message {view.command_msg.id}")
                        await view.command_msg.remove_reaction(Strings.PROCESSING, interaction.client.user)
                        logger.debug(f"[{interaction.user.id}] - Attempting to edit command message {view.command_msg.id} with success message")
                        await view.command_msg.edit(content="Дякую! Не плануєш вихідні.")
                    
                    # Delete buttons message
                    if view.buttons_msg:
                        logger.debug(f"[{interaction.user.id}] - Attempting to delete buttons message {view.buttons_msg.id}")
                        await view.buttons_msg.delete()
                        logger.debug(f"[{interaction.user.id}] - Deleted buttons message {view.buttons_msg.id}")
                    
                    # Continue survey
                    if next_step:
                        from bot.commands.survey import ask_dynamic_step
                        await ask_dynamic_step(interaction.channel, state, next_step)
                    else:
                        from bot.commands.survey import finish_survey
                        await finish_survey(interaction.channel, state)
                        
                else:
                    # Regular slash command
                    logger.info("Processing regular command (non-survey) decline")
                    logger.debug("Entering regular command branch")
                    
                    if view.command_msg:
                        logger.info("Adding processing reaction to command message")
                        await view.command_msg.add_reaction(Strings.PROCESSING)
                    
                    try:
                        logger.debug("Sending webhook for declined days")
                        # Use follow-up for webhook since interaction was deferred
                        logger.debug(f"Sending webhook to command: {view.cmd_or_step}")
                        logger.debug(f"Payload: { {'command': view.cmd_or_step, 'status': 'ok', 'result': {'value': 'Nothing'}} }")
                        
                        try:
                            logger.debug(f"[{interaction.user.id}] - Attempting to send webhook for declined days (regular command)")
                            success, data = await webhook_service.send_webhook(
                                interaction.followup,
                                command=view.cmd_or_step,
                                status="ok",
                                result={"value": "Nothing"}
                            )
                            logger.debug(f"[{interaction.user.id}] - Webhook completed. Success: {success}, Data: {data if data else 'None'}")
                            if not success:
                                logger.error(f"[{interaction.user.id}] - Webhook failed for command: {view.cmd_or_step}")
                        except Exception as webhook_error:
                            logger.error(f"[{interaction.user.id}] - Webhook exception: {str(webhook_error)}", exc_info=True)
                            success = False
                            data = None
                        
                        if success and data and "output" in data:
                            logger.debug(f"[{interaction.user.id}] - Webhook response contains output")
                            if view.command_msg:
                                logger.debug(f"[{interaction.user.id}] - Attempting to update command message with response")
                                await view.command_msg.remove_reaction(Strings.PROCESSING, interaction.client.user)
                                await view.command_msg.edit(content=data["output"])
                        else:
                            logger.warning(f"[{interaction.user.id}] - Webhook response indicates failure")
                            
                    except Exception as e:
                        logger.error(f"[{interaction.user.id}] - Webhook send failed: {str(e)}", exc_info=True)
                        success = False
                        data = None
                        
                        if view.command_msg:
                            error_msg = Strings.DAYOFF_ERROR.format(
                                days="Відмова від вихідних",
                                error=Strings.UNEXPECTED_ERROR
                            )
                            await view.command_msg.remove_reaction(Strings.PROCESSING, interaction.client.user)
                            await view.command_msg.edit(content=error_msg)
                    
                    if success and data and "output" in data:
                        # Update command message with success
                        if view.command_msg:
                            logger.debug(f"[{interaction.user.id}] - Attempting to remove processing reaction from command message {view.command_msg.id}")
                            await view.command_msg.remove_reaction(Strings.PROCESSING, interaction.client.user)
                            logger.debug(f"[{interaction.user.id}] - Attempting to edit command message {view.command_msg.id} with output: {data['output']}")
                            await view.command_msg.edit(content=data["output"])
                        
                        # Delete buttons message
                        if view.buttons_msg:
                            logger.debug(f"[{interaction.user.id}] - Attempting to delete buttons message {view.buttons_msg.id}")
                            await view.buttons_msg.delete()
                            logger.debug(f"[{interaction.user.id}] - Deleted buttons message {view.buttons_msg.id}")
                    else:
                        if view.command_msg:
                            logger.debug(f"[{interaction.user.id}] - Attempting to remove processing reaction from command message {view.command_msg.id}")
                            await view.command_msg.remove_reaction(Strings.PROCESSING, interaction.client.user)
                            error_msg = Strings.DAYOFF_ERROR.format(
                                days="Відмова від вихідних",
                                error=Strings.GENERAL_ERROR
                            )
                            await view.command_msg.edit(content=error_msg)
                            await view.command_msg.add_reaction(Strings.ERROR)
                        if view.buttons_msg:
                            logger.debug(f"[{interaction.user.id}] - Attempting to delete buttons message {view.buttons_msg.id}")
                            await view.buttons_msg.delete()
                        
            except Exception as e:
                logger.error(f"[{interaction.user.id}] - Error in decline button: {e}")
                if view.command_msg:
                    await view.command_msg.remove_reaction(Strings.PROCESSING, interaction.client.user)
                    error_msg = Strings.DAYOFF_ERROR.format(
                        days="Відмова від вихідних",
                        error=Strings.UNEXPECTED_ERROR
                    )
                    await view.command_msg.edit(content=error_msg)
                    await view.command_msg.add_reaction(Strings.ERROR)
                if view.buttons_msg:
                    await view.buttons_msg.delete()

class DayOffView(discord.ui.View):
    def __init__(self, cmd_or_step: str, user_id: str, has_survey: bool = False):
        super().__init__()  # No timeout
        self.cmd_or_step = cmd_or_step
        self.user_id = user_id
        self.has_survey = has_survey
        self.selected_days = []
        self.selected_dates = []
        self.weekday_map = {
            "Понеділок": 0, "Вівторок": 1, "Середа": 2, "Четвер": 3, 
            "П'ятниця": 4, "Субота": 5, "Неділя": 6
        }
        self.command_msg = None  # Reference to the command message
        self.buttons_msg = None  # Reference to the buttons message

    def get_date_for_day(self, day: str) -> datetime.datetime:
        """Get the date for a given weekday name in Kyiv time."""
        # Get current date in Kyiv time
        current_date = datetime.datetime.now(constants.KYIV_TIMEZONE)
        current_weekday = current_date.weekday()
        
        # Calculate target date
        day_number = self.weekday_map[day]
        
        if "day_off_nextweek" in self.cmd_or_step:
            # For next week, add 7 days to get to next week
            days_ahead = day_number - current_weekday + 7
        else:
            # For this week
            days_ahead = day_number - current_weekday
            if days_ahead <= 0 and "day_off_thisweek" in self.cmd_or_step:
                # If the day has passed this week and it's thisweek command,
                # we shouldn't include it (this is a safety check)
                return None
        
        # Calculate target date in Kyiv time
        target_date = current_date + datetime.timedelta(days=days_ahead)
        return target_date

def create_day_off_view(
    cmd_or_step: str,
    user_id: str,
    timeout: Optional[float] = None,
    has_survey: bool = False
) -> DayOffView:
    """Create a day off view with buttons."""
    logger.debug(f"Creating DayOffView for {cmd_or_step}, user {user_id}")
    view = DayOffView(cmd_or_step, user_id, has_survey=has_survey)
    
    # Get current weekday (0 = Monday, 6 = Sunday)
    current_date = datetime.datetime.now()
    current_weekday = current_date.weekday()
    
    logger.debug(f"Creating day off buttons for cmd_or_step: {cmd_or_step}")
    logger.debug(f"Creating day off buttons for command: {cmd_or_step}")
    # Add day off buttons
    days = [
        "Понеділок",
        "Вівторок",
        "Середа",
        "Четвер",
        "П'ятниця",
        "Субота",
        "Неділя"
    ]
    
    for day in days:
        # For thisweek command, skip days that have already passed
        logger.debug(f"Processing day: {day}")
        if "day_off_thisweek" in cmd_or_step and view.weekday_map[day] < current_weekday:
            logger.debug(f"Skipping {day} - already passed this week")
            continue
            
        custom_id = f"day_off_button_{day}_{cmd_or_step}_{user_id}"
        button = DayOffButton(label=day, custom_id=custom_id, cmd_or_step=cmd_or_step)
        view.add_item(button)
    
    # Add confirm and decline buttons
    view.add_item(ConfirmButton())
    view.add_item(DeclineButton())
    
    return view