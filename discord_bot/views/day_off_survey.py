import discord
from typing import Optional, List
import datetime
from config import ViewType, logger, constants, Strings
from services import survey_manager, webhook_service # Import webhook_service
import asyncio

class DayOffButton_survey(discord.ui.Button):
    def __init__(self, *, label: str, custom_id: str, cmd_or_step: str):
        super().__init__(
            style=discord.ButtonStyle.secondary,  # Start with gray color
            label=label,
            custom_id=custom_id
        )
        self.cmd_or_step = cmd_or_step
        self.is_selected = False

    async def callback(self, interaction: discord.Interaction):
        logger.info(f"[{interaction.user.id}] - DayOffButton_survey callback triggered for button: {self.label}")
        from config import Strings # Import Strings locally
        # First, acknowledge the interaction to prevent timeout
        logger.debug(f"[{interaction.user.id}] - Attempting to defer interaction response for DayOffButton_survey")
        if not interaction.response.is_done():
            await interaction.response.defer(ephemeral=False)
        logger.debug(f"[{interaction.user.id}] - Interaction response deferred for DayOffButton_survey")

        # Get the original message
        message = interaction.message
        if message:
            # Add processing reaction
            try:
                logger.debug(f"[{interaction.user.id}] - Attempting to add processing reaction to message {message.id}")
                await message.add_reaction(Strings.PROCESSING)
                logger.debug(f"[{interaction.user.id}] - Added processing reaction to message {message.id}")
            except Exception as e:
                logger.error(f"[{interaction.user.id}] - Error adding processing reaction to message {message.id}: {e}")

        try:
            # Toggle selection
            self.is_selected = not self.is_selected
            logger.debug(f"[{interaction.user.id}] - Button {self.label} selection toggled to: {self.is_selected}")
            self.style = discord.ButtonStyle.primary if self.is_selected else discord.ButtonStyle.secondary

            # Get parent view and update selected days
            view = self.view
            if isinstance(view, DayOffView_survey):
                logger.debug(f"[{interaction.user.id}] - View is DayOffView_survey instance.")
                if self.is_selected:
                    if self.label not in view.selected_days:
                        view.selected_days.append(self.label)
                        logger.debug(f"[{interaction.user.id}] - Added {self.label} to selected_days. Current selected_days: {view.selected_days}")
                else:
                    if self.label in view.selected_days:
                        view.selected_days.remove(self.label)
                        logger.debug(f"[{interaction.user.id}] - Removed {self.label} from selected_days. Current selected_days: {view.selected_days}")

            # Update the message with the new button states
            logger.debug(f"[{interaction.user.id}] - Attempting to edit message {interaction.message.id} with updated view. Selected days before edit: {view.selected_days}")
            await interaction.message.edit(view=self.view)
            logger.debug(f"[{interaction.user.id}] - Message {interaction.message.id} edited with updated view")

            # Show success reaction for survey steps
            if message:
                logger.debug(f"[{interaction.user.id}] - Attempting to remove processing reaction from message {message.id}")
                await message.remove_reaction(Strings.PROCESSING, interaction.client.user)
                logger.debug(f"[{interaction.user.id}] - Removed processing reaction from message {message.id}")

        except Exception as e:
            logger.error(f"[{interaction.user.id}] - Error in day off button callback for button {self.label}: {e}", exc_info=True)
            logger.debug(f"[{interaction.user.id}] - Error details - custom_id: {self.custom_id}, interaction: {interaction.data if interaction else None}")
            if message:
                await message.add_reaction(Strings.ERROR)
                await message.remove_reaction(Strings.PROCESSING, interaction.client.user)
                error_msg = Strings.DAYOFF_ERROR.format(
                    days=self.label,
                    error=Strings.UNEXPECTED_ERROR
                )
                await message.edit(content=error_msg)
                await message.add_reaction(Strings.ERROR)

class ConfirmButton_survey(discord.ui.Button):
    def __init__(self):
        super().__init__(
            style=discord.ButtonStyle.success,
            label="Підтверджую",
            row=4  # Put in the last row
        )

    async def callback(self, interaction: discord.Interaction):
        channel_id = str(interaction.channel.id)
        user_id = str(interaction.user.id)
        logger.info(f"[Channel {channel_id}] - ConfirmButton_survey callback triggered by user {user_id}")
        from config import Strings # Import Strings locally
        from services import webhook_service
        view = self.view
        if isinstance(view, DayOffView_survey):
            # First, acknowledge the interaction to prevent timeout
            logger.debug(f"[Channel {channel_id}] - Attempting to defer interaction response for ConfirmButton_survey by user {user_id}")
            if not interaction.response.is_done(): # Check if already responded
                await interaction.response.defer(ephemeral=False)
            logger.debug(f"[Channel {channel_id}] - Interaction response deferred for ConfirmButton_survey by user {user_id}")

            # Add processing reaction to command message
            if view.command_msg:
                try:
                    logger.debug(f"[Channel {channel_id}] - Attempting to add processing reaction to command message {view.command_msg.id} by user {user_id}")
                    await view.command_msg.add_reaction(Strings.PROCESSING)
                    logger.debug(f"[Channel {channel_id}] - Added processing reaction to command message {view.command_msg.id} by user {user_id}")
                except Exception as e:
                    logger.error(f"[Channel {channel_id}] - Error adding processing reaction to command message {view.command_msg.id} by user {user_id}: {e}")

            try:
                # Convert selected days to dates
                # Convert selected days to dates and format as strings
                formatted_dates = []
                dates_for_log = [] # Keep original datetime objects for logging if needed
                for day in sorted(view.selected_days, key=lambda x: view.weekday_map[x]):
                    date = view.get_date_for_day(day)
                    if date:
                        formatted_dates.append(date.strftime("%Y-%m-%d")) # Format as YYYY-MM-DD
                        dates_for_log.append(date) # Append original datetime for logging
                logger.debug(f"[Channel {channel_id}] - Selected dates (formatted) by user {user_id}: {formatted_dates}")
                logger.debug(f"[Channel {channel_id}] - Selected dates (datetime objects) by user {user_id}: {dates_for_log}")


                if view.has_survey:
                    # Dynamic survey flow
                    state = survey_manager.get_survey(str(interaction.channel.id)) # Get by channel_id
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
                    logger.debug(f"[Channel {channel_id}] - Attempting to send webhook for survey step (ConfirmButton_survey) by user {user_id}: {view.cmd_or_step}")
                    success, data = await webhook_service.send_webhook(
                        interaction,
                        command="survey",
                        status="step",
                        result={
                            "stepName": view.cmd_or_step,
                            "daysSelected": formatted_dates # Use the list of formatted strings
                        }
                    )
                    logger.debug(f"[Channel {channel_id}] - Webhook response for survey step (ConfirmButton_survey) for user {user_id}: success={success}, data={data}")
                    if not success:
                        if view.command_msg:
                            await view.command_msg.remove_reaction(Strings.PROCESSING, interaction.client.user)
                            error_msg = Strings.DAYOFF_ERROR.format(
                                days=', '.join(formatted_dates),
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

                    # Update command message with response
                    if view.command_msg:
                        # Remove processing reaction
                        try:
                            await view.command_msg.remove_reaction(Strings.PROCESSING, interaction.client.user)
                        except:
                            pass # Ignore if reaction wasn't there or couldn't be removed

                        # Update message content with n8n output or default success message
                        output_content = data.get("output", f"Дякую! Вихідні: {', '.join(formatted_dates)} записані.")
                        logger.debug(f"[Channel {channel_id}] - Attempting to edit command message {view.command_msg.id} with output for user {user_id}: {output_content}")
                        await view.command_msg.edit(content=output_content, view=None, attachments=[]) # Remove view/attachments
                        logger.info(f"[Channel {channel_id}] - Updated command message {view.command_msg.id} with response for user {user_id}")

                    # Delete buttons message
                    if view.buttons_msg:
                        logger.debug(f"[Channel {channel_id}] - Attempting to delete buttons message {view.buttons_msg.id} for user {user_id}")
                        await view.buttons_msg.delete()
                        logger.debug(f"[Channel {channel_id}] - Deleted buttons message {view.buttons_msg.id} for user {user_id}")

                    # Continue survey
                    if next_step:
                        from discord_bot.commands.survey import ask_dynamic_step # Corrected import
                        await ask_dynamic_step(self.view.bot_instance, interaction.channel, state, next_step) # Pass bot_instance from view
                    else:
                        from discord_bot.commands.survey import finish_survey # Corrected import
                        await finish_survey(self.view.bot_instance, interaction.channel, state) # Pass bot_instance from view

                else:
                    # Regular slash command
                    # Format dates for n8n (YYYY-MM-DD) in Kyiv time
                    formatted_dates = [
                        view.get_date_for_day(day).strftime("%Y-%m-%d") # Format dates as YYYY-MM-DD
                        for day in sorted(view.selected_days, key=lambda x: view.weekday_map[x])
                        if view.get_date_for_day(day) is not None
                    ]
                    logger.debug(f"[Channel {channel_id}] - Attempting to send webhook for regular command (ConfirmButton_survey) by user {user_id}: {view.cmd_or_step}")
                    success, data = await webhook_service.send_webhook(
                         interaction,
                         command=view.cmd_or_step,
                         status="ok",
                         result={"value": formatted_dates}
                     )
                    logger.debug(f"[Channel {channel_id}] - Webhook response for regular command (ConfirmButton_survey) for user {user_id}: success={success}, data={data}")

                    if success and data and "output" in data:
                        # Update command message with success
                        if view.command_msg:
                            logger.debug(f"[Channel {channel_id}] - Attempting to remove processing reaction from command message {view.command_msg.id} by user {user_id}")
                            await view.command_msg.remove_reaction(Strings.PROCESSING, interaction.client.user)
                            logger.debug(f"[Channel {channel_id}] - Attempting to edit command message {view.command_msg.id} with output for user {user_id}: {data['output']}")
                            await view.command_msg.edit(content=data["output"])

                        # Delete buttons message
                        if view.buttons_msg:
                            logger.debug(f"[Channel {channel_id}] - Attempting to delete buttons message {view.buttons_msg.id} for user {user_id}")
                            await view.buttons_msg.delete()
                            logger.debug(f"[Channel {channel_id}] - Deleted buttons message {view.buttons_msg.id} for user {user_id}")
                    else:
                        if view.command_msg:
                            await view.command_msg.remove_reaction(Strings.PROCESSING, interaction.client.user)
                            error_msg = Strings.DAYOFF_ERROR.format(
                                days=', '.join(formatted_dates),
                                error=Strings.GENERAL_ERROR
                            )
                            await view.command_msg.edit(content=error_msg)
                            await view.command_msg.add_reaction(Strings.ERROR)
                        if view.buttons_msg:
                            await view.buttons_msg.delete()

            except Exception as e:
                logger.error(f"[Channel {channel_id}] - Error in confirm button for user {user_id}: {e}", exc_info=True)
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

class DeclineButton_survey(discord.ui.Button):
    def __init__(self):
        super().__init__(
            style=discord.ButtonStyle.danger,
            label="Не беру",
            row=4  # Put in the last row
        )

    async def callback(self, interaction: discord.Interaction):
        from config import Strings # Import Strings locally
        from services import webhook_service
        view = self.view
        if isinstance(view, DayOffView_survey):
            logger.info(f"DECLINE BUTTON STARTED - User: {interaction.user}, Command: {view.cmd_or_step}")
            logger.debug(f"Decline button clicked by {interaction.user}")
            logger.debug(f"View has_survey: {view.has_survey}, cmd_or_step: {view.cmd_or_step}")

            # Immediately respond to interaction
            try:
                logger.debug(f"[{interaction.user.id}] - Attempting to defer interaction response for DeclineButton_survey")
                await interaction.response.defer(ephemeral=False, thinking=True)
                logger.debug(f"[{interaction.user.id}] - Interaction deferred with thinking state for DeclineButton_survey")
            except Exception as e:
                logger.error(f"Failed to defer interaction: {e}")
                return

            # Add processing reaction to command message
            if view.command_msg:
                try:
                    logger.debug(f"[{interaction.user.id}] - Attempting to add processing reaction to command message {view.command_msg.id}")
                    await view.command_msg.add_reaction(Strings.PROCESSING)
                    logger.debug(f"[{interaction.user.id}] - Added processing reaction to command message {view.command_msg.id}")
                except Exception as e:
                    logger.error(f"[{interaction.user.id}] - Error adding processing reaction to command message {view.command_msg.id}: {e}")
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
                    state = survey_manager.get_survey(str(interaction.channel.id)) # Get by channel_id
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
                    logger.debug(f"[{interaction.user.id}] - Attempting to send webhook for survey step (DeclineButton_survey): {view.cmd_or_step}")
                    success, data = await webhook_service.send_webhook(
                        interaction,
                        command="survey",
                        status="step",
                        result={
                            "stepName": view.cmd_or_step,
                            "daysSelected": ["Nothing"]  # Keep as "Nothing" for backward compatibility
                        }
                    )
                    logger.debug(f"[{interaction.user.id}] - Webhook response for survey step (DeclineButton_survey): success={success}, data={data}")

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
                        # Remove processing reaction
                        try:
                            await view.command_msg.remove_reaction(Strings.PROCESSING, interaction.client.user)
                        except:
                            pass # Ignore if reaction wasn't there or couldn't be removed

                        # Update message content with n8n output or default success message
                        output_content = data.get("output", "Дякую! Не плануєш вихідні.")
                        logger.debug(f"[{interaction.user.id}] - Attempting to edit command message {view.command_msg.id} with output: {output_content}")
                        await view.command_msg.edit(content=output_content, view=None, attachments=[]) # Remove view/attachments

                    # Delete buttons message
                    if view.buttons_msg:
                        logger.debug(f"[{interaction.user.id}] - Attempting to delete buttons message {view.buttons_msg.id}")
                        await view.buttons_msg.delete()
                        logger.debug(f"[{interaction.user.id}] - Deleted buttons message {view.buttons_msg.id}")

                    # Continue survey
                    if next_step:
                        from discord_bot.commands.survey import ask_dynamic_step # Corrected import
                        await ask_dynamic_step(self.bot_instance, interaction.channel, state, next_step) # Pass bot_instance
                    else:
                        from discord_bot.commands.survey import finish_survey # Corrected import
                        await finish_survey(self.bot_instance, interaction.channel, state) # Pass bot_instance

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
                logger.error(f"[{interaction.user.id}] - Error in decline button: {e}", exc_info=True)
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

class DayOffView_survey(discord.ui.View):
    def __init__(self, bot_instance, cmd_or_step: str, user_id: str, has_survey: bool = False, continue_survey_func=None, survey=None, session_id: Optional[str] = None): # Added bot_instance and session_id
        super().__init__(timeout=constants.VIEW_CONFIGS[constants.ViewType.DYNAMIC]["timeout"]) # Use configured timeout
        self.bot_instance = bot_instance # Store bot instance
        self.cmd_or_step = cmd_or_step
        self.user_id = user_id
        self.has_survey = has_survey
        self.selected_days = []
        self.selected_dates = []
        # Use the map from constants
        self.weekday_map = constants.WEEKDAY_MAP
        self.command_msg = None  # Reference to the command message
        self.buttons_msg = None  # Reference to the buttons message
        self.continue_survey_func = continue_survey_func # Store continue survey function
        self.survey = survey # Store the survey object
        self.session_id = session_id # Store session ID


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
            if days_ahead < 0 and "day_off_thisweek" in self.cmd_or_step: # Corrected condition to < 0
                # If the day has passed this week and it's thisweek command,
                # we shouldn't include it (this is a safety check)
                return None

        # Calculate target date in Kyiv time
        target_date = current_date + datetime.timedelta(days=days_ahead)
        return target_date

    async def on_timeout(self):
        logger.warning(f"DayOffView_survey timed out for user {self.user_id}")
        # Attempt to remove the buttons message if it exists
        if self.buttons_msg:
            try:
                await self.buttons_msg.delete()
                logger.debug(f"Deleted timed out buttons message {self.buttons_msg.id}")
            except discord.errors.NotFound:
                logger.debug(f"Buttons message {self.buttons_msg.id} already deleted.")
            except Exception as e:
                logger.error(f"Error deleting timed out buttons message {self.buttons_msg.id}: {e}")

        # Optionally, update the command message to indicate timeout
        if self.command_msg:
            try:
                await self.command_msg.edit(content="Ця взаємодія вичерпала час очікування.", view=None)
                logger.debug(f"Updated command message {self.command_msg.id} with timeout message.")
            except Exception as e:
                logger.error(f"Error updating command message {self.command_msg.id} on timeout: {e}")


def create_day_off_view(
    bot_instance,
    cmd_or_step: str,
    user_id: str,
    has_survey: bool = False,
    continue_survey_func=None,
    survey=None,
    session_id: Optional[str] = None, # Added session_id
    command_msg: Optional[discord.Message] = None, # Added command_msg
    buttons_msg: Optional[discord.Message] = None # Added buttons_msg
):
    """Creates a DayOffView_survey with buttons for each day of the week."""
    view = DayOffView_survey(
        bot_instance,
        cmd_or_step,
        user_id,
        has_survey,
        continue_survey_func,
        survey,
        session_id # Pass session_id
    )
    view.command_msg = command_msg # Set command_msg
    view.buttons_msg = buttons_msg # Set buttons_msg

    # Get the current date in Kyiv time
    current_date = datetime.datetime.now(constants.KYIV_TIMEZONE)
    current_weekday = current_date.weekday() # Monday is 0, Sunday is 6

    # Determine the start date for the view
    if "day_off_nextweek" in cmd_or_step:
        # Start from the next Monday
        days_until_next_monday = (7 - current_weekday) % 7
        if days_until_next_monday == 0: # If today is Monday, next Monday is in 7 days
             days_until_next_monday = 7
        start_date = current_date + datetime.timedelta(days=days_until_next_monday)
    else: # Assuming "day_off_thisweek" or similar
        # Start from today
        start_date = current_date

    # Create buttons for the next 7 days starting from start_date
    for i in range(7):
        date_to_show = start_date + datetime.timedelta(days=i)
        day_name = constants.WEEKDAY_OPTIONS[date_to_show.weekday()].label
        button = DayOffButton_survey(
            label=day_name,
            custom_id=f"day_off_{day_name.lower()}_{user_id}",
            cmd_or_step=cmd_or_step
        )
        view.add_item(button)

    # Add Confirm and Decline buttons
    view.add_item(ConfirmButton_survey())
    view.add_item(DeclineButton_survey())

    return view