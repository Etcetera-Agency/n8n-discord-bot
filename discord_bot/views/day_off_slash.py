import logging
logger = logging.getLogger(__name__)
import discord # type: ignore
from typing import Optional, List
import datetime
from config import ViewType, logger, constants, Strings
import asyncio

class DayOffButton_slash(discord.ui.Button):
    def __init__(self, *, label: str, custom_id: str, cmd_or_step: str):
        super().__init__(
            style=discord.ButtonStyle.secondary,  # Start with gray color
            label=label,
            custom_id=custom_id
        )
        self.cmd_or_step = cmd_or_step
        self.is_selected = False
        
    async def callback(self, interaction: discord.Interaction):
        from config import Strings # Import Strings locally
        # First, acknowledge the interaction to prevent timeout
        logger.debug(f"[Channel {interaction.channel.id}] - Attempting to defer interaction response for DayOffButton_slash")
        if not interaction.response.is_done():
            await interaction.response.defer(ephemeral=False)
        logger.debug(f"[Channel {interaction.channel.id}] - Interaction response deferred for DayOffButton_slash")
        
        # Get the original message
        message = interaction.message
        if message:
            # Add processing reaction
            try:
                logger.debug(f"[Channel {interaction.channel.id}] - Attempting to add processing reaction to message {message.id}")
                await message.add_reaction(Strings.PROCESSING)
                logger.debug(f"[Channel {interaction.channel.id}] - Added processing reaction to message {message.id}")
            except Exception as e:
                logger.error(f"[Channel {interaction.channel.id}] - Error adding processing reaction to message {message.id}: {e}")
            
        try:
            # Toggle selection
            self.is_selected = not self.is_selected
            logger.debug(f"[Channel {interaction.channel.id}] - Button '{self.label}' selection toggled to: {self.is_selected}")
            self.style = discord.ButtonStyle.primary if self.is_selected else discord.ButtonStyle.secondary
            
            # Get parent view and update selected days
            view = self.view
            if isinstance(view, DayOffView_slash):
                if self.is_selected:
                    if self.label not in view.selected_days:
                        view.selected_days.append(self.label)
                        logger.debug(f"[Channel {interaction.channel.id}] - Added '{self.label}' to selected_days. Current selected_days: {view.selected_days}")
                else:
                    if self.label in view.selected_days:
                        view.selected_days.remove(self.label)
                        logger.debug(f"[Channel {interaction.channel.id}] - Removed '{self.label}' from selected_days. Current selected_days: {view.selected_days}")
            
            # Update the message with the new button states
            logger.debug(f"[Channel {interaction.channel.id}] - Attempting to edit message {interaction.message.id} with updated view")
            await interaction.message.edit(view=self.view)
            logger.debug(f"[Channel {interaction.channel.id}] - Message {interaction.message.id} edited with updated view")
            
            # Show success reaction for survey steps
            if message:
                logger.debug(f"[Channel {interaction.channel.id}] - Attempting to remove processing reaction from message {message.id}")
                await message.remove_reaction(Strings.PROCESSING, interaction.client.user)
                logger.debug(f"[Channel {interaction.channel.id}] - Removed processing reaction from message {message.id}")
                
        except Exception as e:
            logger.error(f"Error in day off button callback: {e}")
            logger.debug(f"Error details - custom_id: {self.custom_id}, interaction: {interaction.data if interaction else None}")
            if message:
                await message.add_reaction(Strings.ERROR)
                await message.remove_reaction(Strings.PROCESSING, interaction.client.user)
                error_msg = Strings.DAYOFF_ERROR.format(
                    days=self.label,
                    error=Strings.UNEXPECTED_ERROR
                )
                await message.edit(content=error_msg)
                await message.add_reaction(Strings.ERROR)

class ConfirmButton_slash(discord.ui.Button):
    def __init__(self):
        super().__init__(
            style=discord.ButtonStyle.success,
            label="Підтверджую",
            row=4  # Put in the last row
        )
        
    async def callback(self, interaction: discord.Interaction):
        from config import Strings # Import Strings locally
        from services import webhook_service
        view = self.view
        if isinstance(view, DayOffView_slash):
            # First, acknowledge the interaction to prevent timeout
            logger.debug(f"[Channel {interaction.channel.id}]  - Attempting to defer interaction response for ConfirmButton_slash")
            if not interaction.response.is_done():
                await interaction.response.defer(ephemeral=False)
            logger.debug(f"[Channel {interaction.channel.id}] - Interaction response deferred for ConfirmButton_slash")
            
            # Delete buttons message
            if view.buttons_msg:
                try:
                    logger.debug(f"[Channel {interaction.channel.id}] - Attempting to delete buttons message {getattr(view.buttons_msg, 'id', 'N/A')}")
                    await view.buttons_msg.delete()
                    logger.debug(f"[Channel {interaction.channel.id}] - Deleted buttons message {getattr(view.buttons_msg, 'id', 'N/A')}")
                    view.stop() # Stop the view since buttons are gone
                except Exception as e:
                    logger.error(f"[Channel {interaction.channel.id}] - Error deleting buttons message {view.buttons_msg.id}: {e}")

            # Add processing reaction to command message
            if view.command_msg:
                try:
                    logger.debug(f"[Channel {interaction.channel.id}] - Attempting to add processing reaction to message {view.command_msg.id}")
                    await view.command_msg.add_reaction(Strings.PROCESSING)
                    logger.debug(f"[Channel {interaction.channel.id}] - Added processing reaction to command message {view.command_msg.id}")
                except Exception as e:
                    logger.error(f"[Channel {interaction.channel.id}] - Error adding processing reaction to command message {view.command_msg.id}: {e}")

            try:
                # Convert selected days to dates
                logger.debug(f"[Channel {interaction.channel.id}] - Selected days before processing: {view.selected_days}")
                dates = []
                for day in sorted(view.selected_days, key=lambda x: view.weekday_map[x]):
                    date = view.get_date_for_day(day)
                    if date:
                        dates.append(date)
                # Regular slash command
                # Format dates for n8n (YYYY-MM-DD) in Kyiv time
                formatted_dates = [
                    date.strftime("%Y-%m-%d")
                    for day in sorted(view.selected_days, key=lambda x: view.weekday_map[x])
                    if (date := view.get_date_for_day(day)) is not None
                ]
                logger.debug(f"[Channel {interaction.channel.id}] - Formatted dates for webhook: {formatted_dates}")

                logger.debug(f"[Channel {interaction.channel.id}] - Attempting to send webhook for regular command (ConfirmButton_slash): {view.cmd_or_step}")
                success, data = await webhook_service.send_webhook(
                     interaction, # Use interaction directly
                     command=view.cmd_or_step,
                     status="ok",
                     result={"value": formatted_dates}
                 )
                logger.debug(f"[Channel {interaction.channel.id}] - Webhook response for regular command (ConfirmButton_slash): success={success}, data={data}")

                # Update command message based on webhook response
                if view.command_msg:
                    try:
                        await view.command_msg.remove_reaction(Strings.PROCESSING, interaction.client.user)
                        if success and data and "output" in data:
                            logger.debug(f"[Channel {interaction.channel.id}] - Attempting to edit command message {getattr(view.command_msg, 'id', 'N/A')} with output: {data['output']}")
                            output_content = data["output"]
                            if view.selected_days and Strings.MENTION_MESSAGE not in output_content: # Check if any days were selected AND message is not already present
                                output_content += Strings.MENTION_MESSAGE
                            await view.command_msg.edit(content=output_content)
                        else:
                            logger.warning(f"[Channel {interaction.channel.id}] - Webhook response indicates failure or no output. Editing command message {view.command_msg.id} with error.")
                            error_msg = Strings.DAYOFF_ERROR.format(
                                days=', '.join(dates),
                                error=Strings.GENERAL_ERROR
                            )
                            await view.command_msg.edit(content=error_msg)
                            await view.command_msg.add_reaction(Strings.ERROR)
                    except Exception as edit_error:
                        logger.error(f"[Channel {interaction.channel.id}] - Error editing command message {view.command_msg.id}: {edit_error}")

            except Exception as e:
                logger.error(f"Error in confirm button: {e}")
                if view.command_msg:
                    try:
                        await view.command_msg.remove_reaction(Strings.PROCESSING, interaction.client.user)
                        error_msg = Strings.DAYOFF_ERROR.format(
                            days=', '.join(view.selected_days),
                            error=Strings.UNEXPECTED_ERROR
                        )
                        await view.command_msg.edit(content=error_msg)
                        await view.command_msg.add_reaction(Strings.ERROR)
                    except Exception as edit_error:
                        logger.error(f"[Channel {interaction.channel.id}] - Error editing command message {view.command_msg.id} after exception: {edit_error}")
class DeclineButton_slash(discord.ui.Button):
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
        if isinstance(view, DayOffView_slash):
            logger.info(f"DECLINE BUTTON STARTED - User: {interaction.user}, Command: {view.cmd_or_step}")
            logger.debug(f"Decline button clicked by {interaction.user}")
            logger.debug(f"View has_survey: {view.has_survey}, cmd_or_step: {view.cmd_or_step}")
            
            # Immediately respond to interaction
            try:
                logger.debug(f"[Channel {interaction.channel.id}] - Attempting to defer interaction response for DeclineButton_slash")
                await interaction.response.defer(ephemeral=False)
                logger.debug(f"[Channel {interaction.channel.id}] - Interaction deferred for DeclineButton_slash")
            except Exception as e:
                logger.error(f"Failed to defer interaction: {e}")
                return
            # Delete buttons message
            if view.buttons_msg:
                try:
                    logger.debug(f"[Channel {interaction.channel.id}] - Attempting to delete buttons message {getattr(view.buttons_msg, 'id', 'N/A')}")
                    await view.buttons_msg.delete()
                    logger.debug(f"[Channel {interaction.channel.id}] - Deleted buttons message {getattr(view.buttons_msg, 'id', 'N/A')}")
                    view.stop() # Stop the view since buttons are gone
                except Exception as e:
                    logger.error(f"[Channel {interaction.channel.id}] - Error deleting buttons message {view.buttons_msg.id}: {e}")

            # Add processing reaction to command message
            if view.command_msg:
                try:
                    logger.debug(f"[Channel {interaction.channel.id}] - Attempting to add processing reaction to message {view.command_msg.id}")
                    await view.command_msg.add_reaction(Strings.PROCESSING)
                    logger.debug(f"[Channel {interaction.channel.id}] - Added processing reaction to command message {view.command_msg.id}")
                except Exception as e:
                    logger.error(f"[Channel {interaction.channel.id}] - Error adding processing reaction to command message {view.command_msg.id}: {e}")

            try:
                logger.debug(f"[Channel {interaction.channel.id}] - Attempting to send webhook for declined days (regular command)")
                success, data = await webhook_service.send_webhook(
                    interaction, # Use interaction directly
                    command=view.cmd_or_step,
                    status="ok",
                    result={"value": "Nothing"} # Send "Nothing" as result
                )
                logger.debug(f"[Channel {interaction.channel.id}] - Webhook completed. Success: {success}, Data: {data if data else 'None'}")
                if not success:
                    logger.error(f"[Channel {interaction.channel.id}] - Webhook failed for command: {view.cmd_or_step}")

                # Update command message based on webhook response
                if view.command_msg:
                    try:
                        await view.command_msg.remove_reaction(Strings.PROCESSING, interaction.client.user)
                        if success and data and "output" in data:
                            logger.debug(f"[Channel {interaction.channel.id}] - Attempting to edit command message {getattr(view.command_msg, 'id', 'N/A')} with output: {data['output']}")
                            await view.command_msg.edit(content=data["output"])
                        else:
                            logger.warning(f"[Channel {interaction.channel.id}] - Webhook response indicates failure or no output. Editing command message {view.command_msg.id} with error.")
                            error_msg = Strings.DAYOFF_ERROR.format(
                                days="Відмова від вихідних",
                                error=Strings.GENERAL_ERROR
                            )
                            await view.command_msg.edit(content=error_msg)
                            await view.command_msg.add_reaction(Strings.ERROR)
                    except Exception as edit_error:
                        logger.error(f"[Channel {interaction.channel.id}] - Error editing command message {view.command_msg.id}: {edit_error}")

            except Exception as e:
                logger.error(f"[Channel {interaction.channel.id}] - Error in decline button: {e}")
                if view.command_msg:
                    try:
                        await view.command_msg.remove_reaction(Strings.PROCESSING, interaction.client.user)
                        error_msg = Strings.DAYOFF_ERROR.format(
                            days="Відмова від вихідних",
                            error=Strings.UNEXPECTED_ERROR
                        )
                        await view.command_msg.edit(content=error_msg)
                        await view.command_msg.add_reaction(Strings.ERROR)
                    except Exception as edit_error:
                        logger.error(f"[Channel {interaction.channel.id}] - Error editing command message {view.command_msg.id} after exception: {edit_error}")
                    logger.debug(f"[Channel {interaction.channel.id}] - Deleted buttons message {getattr(view.buttons_msg, 'id', 'N/A')}")

class DayOffView_slash(discord.ui.View):
    def __init__(self, cmd_or_step: str, user_id: str, has_survey: bool = False):
        super().__init__(timeout=constants.VIEW_CONFIGS[constants.ViewType.DYNAMIC]["timeout"])
        self.cmd_or_step = cmd_or_step
        self.user_id = user_id
        self.has_survey = has_survey
        self.selected_days = []
        self.selected_dates = []
        # Use the map from constants
        self.weekday_map = constants.WEEKDAY_MAP
        self.command_msg: Optional[discord.Message] = None  # Reference to the command message
        self.buttons_msg: Optional[discord.Message] = None  # Reference to the buttons message

    def get_date_for_day(self, day: str) -> Optional[datetime.datetime]:
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
    
    async def on_timeout(self):
        channel_id = self.command_msg.channel.id if self.command_msg else "unknown"
        logger.warning(f"[Channel {channel_id}] DayOffView_slash timed out for user {self.user_id}")
        
        # Update original command message with timeout notification
        if self.command_msg:
            try:
                # Get first 13 characters of timeout message
                from config import Strings
                timeout_msg = Strings.TIMEOUT_MESSAGE[:13]
                await self.command_msg.edit(
                    content=f"{self.command_msg.content}\n{timeout_msg}"
                )
            except Exception as e:
                logger.error(f"Failed to update command message on timeout: {e}")
        
        # Clean up buttons message
        if self.buttons_msg:
            try:
                await self.buttons_msg.delete()
            except:
                pass # Ignore if already deleted
        self.stop() # Stop the view since it timed out

def create_day_off_view(
    cmd_or_step: str,
    user_id: str,
    timeout: Optional[float] = None,
    has_survey: bool = False
) -> DayOffView_slash:
    """Create a day off view with buttons."""
    logger.debug(f"Creating DayOffView_slash for {cmd_or_step}, user {user_id}")
    view = DayOffView_slash(cmd_or_step, user_id, has_survey=has_survey)
    
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
        button = DayOffButton_slash(label=day, custom_id=custom_id, cmd_or_step=cmd_or_step)
        view.add_item(button)
    
    # Add confirm and decline buttons
    view.add_item(ConfirmButton_slash())
    view.add_item(DeclineButton_slash())
    
    return view
