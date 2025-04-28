import logging
logger = logging.getLogger(__name__)
import discord # type: ignore
from typing import Optional, List
import datetime
from config import ViewType, logger, constants
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
        from config import Strings # Import Strings locally
        # First, acknowledge the interaction to prevent timeout
        logger.debug(f"[{interaction.user.id}] - Attempting to defer interaction response for DayOffButton")
        if not interaction.response.is_done():
            await interaction.response.defer(ephemeral=False)
        logger.debug(f"[{interaction.user.id}] - Interaction response deferred for DayOffButton")
        
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
            logger.debug(f"[{interaction.user.id}] - Button '{self.label}' selection toggled to: {self.is_selected}")
            self.style = discord.ButtonStyle.primary if self.is_selected else discord.ButtonStyle.secondary
            
            # Get parent view and update selected days
            view = self.view
            if isinstance(view, DayOffView):
                if self.is_selected:
                    if self.label not in view.selected_days:
                        view.selected_days.append(self.label)
                        logger.debug(f"[{interaction.user.id}] - Added '{self.label}' to selected_days. Current selected_days: {view.selected_days}")
                else:
                    if self.label in view.selected_days:
                        view.selected_days.remove(self.label)
                        logger.debug(f"[{interaction.user.id}] - Removed '{self.label}' from selected_days. Current selected_days: {view.selected_days}")
            
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
                await message.add_reaction(Strings.ERROR)
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
        from config import Strings # Import Strings locally
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
                try:
                    logger.debug(f"[{interaction.user.id}] - Attempting to add processing reaction to message {view.command_msg.id}")
                    await view.command_msg.add_reaction(Strings.PROCESSING)
                    logger.debug(f"[{interaction.user.id}] - Added processing reaction to command message {view.command_msg.id}")
                except Exception as e:
                    logger.error(f"[{interaction.user.id}] - Error adding processing reaction to command message {view.command_msg.id}: {e}")
            
            try:
                # Convert selected days to dates
                logger.debug(f"[{interaction.user.id}] - Selected days before processing: {view.selected_days}")
                dates = []
                for day in sorted(view.selected_days, key=lambda x: view.weekday_map[x]):
                    date = view.get_date_for_day(day)
                    if date:
                        dates.append(date)
                # Regular slash command
                # Format dates for n8n (YYYY-MM-DD) in Kyiv time
                formatted_dates = [
                    view.get_date_for_day(day).strftime("%Y-%m-%d")
                    for day in sorted(view.selected_days, key=lambda x: view.weekday_map[x])
                    if view.get_date_for_day(day) is not None
                ]
                logger.debug(f"[{interaction.user.id}] - Formatted dates for webhook: {formatted_dates}")
                
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
        from config import Strings # Import Strings locally
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
                except Exception as e:
                    logger.error(f"[{interaction.user.id}] - Error during webhook sending process: {e}", exc_info=True)
                    success = False
                    data = None

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
