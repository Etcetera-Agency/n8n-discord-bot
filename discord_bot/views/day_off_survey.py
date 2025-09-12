import discord # type: ignore
from typing import Optional
import datetime
from config import logger, constants
from services import survey_manager # Import webhook_service

class DayOffView_survey(discord.ui.View):
    def __init__(self, bot_instance, cmd_or_step: str, user_id: str, has_survey: bool = False, continue_survey_func=None, survey=None, session_id: Optional[str] = None):
        # Prioritize survey's session_id if available
        self.session_id = ""
        if session_id:
            self.session_id = session_id
        elif survey and survey.session_id:
            self.session_id = survey.session_id
        logger.debug(f"[Channel {self.session_id.split('_')[0]}] - DayOffView_survey.__init__ called for cmd_or_step: {cmd_or_step}, has_survey: {has_survey}")
        super().__init__(timeout=constants.VIEW_CONFIGS[constants.ViewType.DYNAMIC]["timeout"])
        logger.debug(f"[Channel {self.session_id.split('_')[0]}] - DayOffView_survey initialized with timeout: {self.timeout}")
        self.bot_instance = bot_instance
        self.cmd_or_step = cmd_or_step
        self.user_id = user_id
        self.has_survey = has_survey
        self.selected_days = []
        self.selected_dates = []
        self.weekday_map = constants.WEEKDAY_MAP
        self.command_msg: Optional[discord.Message] = None
        self.buttons_msg: Optional[discord.Message] = None
        self.continue_survey_func = continue_survey_func
        self.survey = survey
        logger.debug(f"[Channel {self.session_id.split('_')[0]}] - DayOffView_survey initialized. command_msg: {self.command_msg}, buttons_msg: {self.buttons_msg}")


    def get_date_for_day(self, day: str) -> Optional[datetime.datetime]:
        """Get the date for a given weekday name in Kyiv time."""
        current_date = datetime.datetime.now(constants.KYIV_TIMEZONE)
        current_weekday = current_date.weekday()

        day_number = self.weekday_map[day]

        if "day_off_nextweek" in self.cmd_or_step:
            days_ahead = day_number - current_weekday + 7
        else:
            days_ahead = day_number - current_weekday
            if days_ahead < 0 and "day_off_thisweek" in self.cmd_or_step:
                return None

        target_date = current_date + datetime.timedelta(days=days_ahead)
        return target_date

    async def on_timeout(self):
        logger.warning(f"DayOffView_survey timed out for session {self.session_id}")
        # Clean up view first
        if self.buttons_msg:
            try:
                await self.buttons_msg.delete()
                logger.info(f"[Channel {self.session_id.split('_')[0]}] - Deleted buttons message {self.buttons_msg.id} on timeout.")
            except discord.NotFound:
                logger.warning(f"[Channel {self.session_id.split('_')[0]}] - Buttons message {self.buttons_msg.id} already deleted on timeout.")
            except Exception as e:
                logger.error(f"[Channel {self.session_id.split('_')[0]}] - Error deleting buttons message on timeout: {e}")
            finally:
                self.buttons_msg = None
                self.stop()

        # Skip survey timeout handling if survey was already removed
        # This prevents duplicate cleanup and timeout messages
        if not survey_manager.get_survey_by_session(self.session_id):
            logger.info(f"[Channel {self.session_id.split('_')[0]}] - Survey already removed, skipping timeout handling")
            return

        # Handle survey timeout
        if self.has_survey and self.bot_instance and self.session_id:
            logger.info(f"[Channel {self.session_id.split('_')[0]}] - Calling handle_survey_incomplete on timeout for session {self.session_id}")
            from discord_bot.commands.survey import handle_survey_incomplete # Import locally to avoid circular dependency
            await handle_survey_incomplete(self.bot_instance, self.session_id)
        else:
            logger.warning(f"[Channel {self.session_id.split('_')[0] if self.session_id else 'N/A'}] - Cannot call handle_survey_incomplete on timeout. has_survey: {self.has_survey}, bot_instance: {bool(self.bot_instance)}, session_id: {self.session_id}")


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
            logger.info(f"Processing ConfirmButton_survey callback - view user: {view.user_id}, interaction user: {interaction.user.id}")

            if view.command_msg:
                try:
                    logger.debug(f"[Channel {channel_id}] - Attempting to add processing reaction to command message {view.command_msg.id} by user {user_id}")
                    await view.command_msg.add_reaction(Strings.PROCESSING)
                    logger.debug(f"[Channel {channel_id}] - Added processing reaction to command message {view.command_msg.id} by user {user_id}")
                except Exception as e:
                    logger.error(f"[Channel {channel_id}] - Error adding processing reaction to command message {getattr(view.command_msg, 'id', 'N/A')}: {e}", exc_info=True)

            try:
                formatted_dates = []
                for day in sorted(view.selected_days, key=lambda x: view.weekday_map[x]):
                    date = view.get_date_for_day(day)
                    if date:
                        formatted_dates.append(date.strftime("%Y-%m-%d"))
                logger.debug(f"[Channel {channel_id}] - Selected dates (formatted) by user {user_id}: {formatted_dates}")

                state = survey_manager.get_survey(str(interaction.channel.id))
                logger.debug(f"[Channel {channel_id}] - survey_manager.get_survey returned: {state}.")

                if view.buttons_msg:
                    try:
                        await view.buttons_msg.delete()
                        logger.info(f"[Channel {channel_id}] - Successfully deleted buttons message ID: {view.buttons_msg.id}")
                        view.buttons_msg = None
                        view.stop()
                    except discord.NotFound:
                        logger.warning(f"[Channel {channel_id}] - Buttons message {getattr(view.buttons_msg, 'id', 'N/A')} already deleted or not found.")
                        view.buttons_msg = None
                    except Exception as delete_error:
                        logger.error(f"[Channel {channel_id}] - Error deleting buttons message {getattr(view.buttons_msg, 'id', 'N/A')}: {delete_error}", exc_info=True)
                else:
                    logger.warning(f"[Channel {channel_id}] - view.buttons_msg is None or False, cannot delete.")

                if state:
                    logger.info(f"Found survey for channel {channel_id}, current step: {state.current_step()}")

                    result_payload = {
                        "stepName": view.cmd_or_step,
                        "daysSelected": formatted_dates
                    }
                    logger.info(f"[Channel {channel_id}] - Sending webhook for survey step: {view.cmd_or_step} with value: {formatted_dates}")
                    success, data = await webhook_service.send_webhook(
                        interaction,
                        command="survey",
                        status="step",
                        result=result_payload
                    )
                    logger.info(f"[Channel {channel_id}] - Webhook sending result for survey step: success={success}, data={data}")

                    logger.debug(f"Webhook response for survey step: success={success}, data={data}")
                    flag = (data or {}).get("survey")
                    try:
                        if flag == "continue":
                            logger.debug(f"[Channel {channel_id}] - Advancing and continuing survey")
                            state.next_step()
                            if view.continue_survey_func:
                                await view.continue_survey_func(interaction.channel, state)
                        elif flag == "end":
                            logger.debug(f"[Channel {channel_id}] - Advancing and finishing survey")
                            state.next_step()
                            from discord_bot.commands.survey import finish_survey as _finish
                            await _finish(view.bot_instance, interaction.channel, state)
                        elif flag == "cancel":
                            logger.debug(f"[Channel {channel_id}] - Cancelling survey per n8n instruction")
                            survey_manager.remove_survey(str(interaction.channel.id))
                        else:
                            logger.debug(f"[Channel {channel_id}] - No flag; default continue path")
                            state.next_step()
                            if view.continue_survey_func:
                                await view.continue_survey_func(interaction.channel, state)
                    except Exception as e:
                        logger.error(f"[Channel {channel_id}] - Error handling survey flow after webhook: {e}", exc_info=True)

                    if not success:
                        logger.error(f"Failed to send webhook for survey step: {view.cmd_or_step}")
                        if view.command_msg:
                            await view.command_msg.remove_reaction(Strings.PROCESSING, interaction.client.user)
                            error_msg = Strings.DAYOFF_ERROR.format(
                                days=', '.join(formatted_dates),
                                error=Strings.GENERAL_ERROR
                            )
                            await view.command_msg.edit(content=error_msg)
                            await view.command_msg.add_reaction(Strings.ERROR)
                        return

                    state.results[view.cmd_or_step] = formatted_dates
                    logger.info(f"Updated survey results: {state.results}")

                    if view.command_msg:
                        try:
                            await view.command_msg.remove_reaction(Strings.PROCESSING, interaction.client.user)
                            output_content = data.get("output", f"Дякую! Вихідні: {', '.join(formatted_dates)} записані.") if data else f"Дякую! Вихідні: {', '.join(formatted_dates)} записані."
                            if formatted_dates and Strings.MENTION_MESSAGE not in output_content:
                                output_content += Strings.MENTION_MESSAGE
                            await view.command_msg.edit(content=output_content, view=None, attachments=[])
                            logger.info(f"[Channel {channel_id}] - Updated command message {view.command_msg.id} with response for user {user_id}")
                        except Exception as edit_error:
                            logger.error(f"[Channel {channel_id}] - Error editing command message {getattr(view.command_msg, 'id', 'N/A')}: {edit_error}", exc_info=True)

                    logger.info(f"Survey state before continuation - current step: {state.current_step()}, results: {state.results}")

                    if not state or not state.user_id:
                        logger.error("Invalid survey state for continuation")
                        return

                else:
                    logger.warning(f"[Channel {channel_id}] - No active survey state found for user in confirm button callback. Treating as non-survey command or expired survey.")

                    if view.has_survey:
                        logger.error(f"[Channel {channel_id}] - Survey initiated but state not found in callback for step {view.cmd_or_step}.")
                        try:
                            if interaction.response.is_done():
                                logger.debug(f"[Channel {channel_id}] - interaction.response.is_done()=True, using followup.send for expired survey")
                                await interaction.followup.send(Strings.SURVEY_EXPIRED_OR_NOT_FOUND, ephemeral=True)
                            else:
                                logger.debug(f"[Channel {channel_id}] - interaction.response.is_done()=False, using response.send_message for expired survey")
                                await interaction.response.send_message(Strings.SURVEY_EXPIRED_OR_NOT_FOUND, ephemeral=True)
                        except Exception as e:
                            logger.error(f"[Channel {channel_id}] - Failed to send survey expired message: {e}")

                        if view.buttons_msg:
                            try:
                                await view.buttons_msg.delete()
                            except Exception as e:
                                logger.warning(f"[Channel {channel_id}] - Failed to delete buttons message after expired survey message: {e}")

                    else:
                        logger.error(f"[Channel {channel_id}] - Confirm button clicked in non-survey context (has_survey=False) for command: {view.cmd_or_step}. No active survey state found.")
                        if view.command_msg:
                            try:
                                await view.command_msg.edit(content=Strings.GENERAL_ERROR, view=None)
                            except Exception as e:
                                logger.error(f"[Channel {channel_id}] - Error editing command message with general error: {e}")
                        if view.buttons_msg:
                            try:
                                await view.buttons_msg.delete()
                            except Exception as e:
                                logger.error(f"[Channel {channel_id}] - Error deleting buttons message: {e}")
                        view.stop()
            except Exception as e:
                session_id_for_log = view.session_id.split('_')[0] if view and view.session_id else 'N/A'
                logger.error(f"[Channel {session_id_for_log}] - Error in confirm button callback: {e}", exc_info=True)
                if view and view.command_msg:
                    await view.command_msg.remove_reaction(Strings.PROCESSING, interaction.client.user)
                    error_msg = Strings.DAYOFF_ERROR.format(
                        days=', '.join(view.selected_days),
                        error=Strings.UNEXPECTED_ERROR
                    )
                    await view.command_msg.edit(content=error_msg)
                    await view.command_msg.add_reaction(Strings.ERROR)
                logger.error(f"[Channel {session_id_for_log}] - Failed to send error response in confirm callback: {e}")
            finally:
                if view and view.buttons_msg:
                    try:
                        await view.buttons_msg.delete()
                        session_id_for_log = view.session_id.split('_')[0] if view and view.session_id else 'N/A'
                        logger.info(f"[Channel {session_id_for_log}] - Successfully deleted buttons message in finally block.")
                        view.stop()
                    except discord.NotFound:
                        session_id_for_log = view.session_id.split('_')[0] if view and view.session_id else 'N/A'
                        logger.warning(f"[Channel {session_id_for_log}] - Buttons message already deleted or not found in finally block.")
                    except Exception as e:
                        session_id_for_log = view.session_id.split('_')[0] if view and view.session_id else 'N/A'
                        logger.error(f"[Channel {session_id_for_log}] - Error deleting buttons message in finally block: {e}", exc_info=True)

class DeclineButton_survey(discord.ui.Button):
    def __init__(self):
        super().__init__(
            style=discord.ButtonStyle.danger,
            label="Не беру",
            row=4  # Put in the last row
        )

    async def callback(self, interaction: discord.Interaction):
        channel_id = str(interaction.channel.id)
        user_id = str(interaction.user.id)
        logger.info(f"[Channel {channel_id}] - DeclineButton_survey callback triggered by user {user_id}")
        from config import Strings # Import Strings locally
        from services import webhook_service
        view = self.view
        if isinstance(view, DayOffView_survey):
            logger.info(f"Processing DeclineButton_survey callback - view user: {view.user_id}, interaction user: {interaction.user.id}")

            if view.command_msg:
                try:
                    logger.debug(f"[Channel {channel_id}] - Attempting to add processing reaction to command message {view.command_msg.id} by user {user_id}")
                    await view.command_msg.add_reaction(Strings.PROCESSING)
                    logger.debug(f"[Channel {channel_id}] - Added processing reaction to command message {view.command_msg.id} by user {user_id}")
                except Exception as e:
                    logger.error(f"[Channel {channel_id}] - Error adding processing reaction to command message {getattr(view.command_msg, 'id', 'N/A')}: {e}", exc_info=True)

            try:
                state = survey_manager.get_survey(str(interaction.channel.id))
                logger.debug(f"[Channel {channel_id}] - survey_manager.get_survey returned: {state}.")

                if view.buttons_msg:
                    try:
                        await view.buttons_msg.delete()
                        logger.info(f"[Channel {channel_id}] - Successfully deleted buttons message ID: {view.buttons_msg.id}")
                        view.buttons_msg = None
                        view.stop()
                    except discord.NotFound:
                        logger.warning(f"[Channel {channel_id}] - Buttons message {getattr(view.buttons_msg, 'id', 'N/A')} already deleted or not found.")
                        view.buttons_msg = None
                    except Exception as delete_error:
                        logger.error(f"[Channel {channel_id}] - Error deleting buttons message {getattr(view.buttons_msg, 'id', 'N/A')}: {delete_error}", exc_info=True)
                else:
                    logger.warning(f"[Channel {channel_id}] - view.buttons_msg is None or False, cannot delete.")

                if state:
                    logger.info(f"Found survey for channel {channel_id}, current step: {state.current_step()}")

                    result_payload = {
                        "stepName": view.cmd_or_step,
                        "daysSelected": ["Nothing"]
                    }
                    logger.info(f"[Channel {channel_id}] - Sending webhook for survey step: {view.cmd_or_step} with value: Nothing")
                    success, data = await webhook_service.send_webhook(
                        interaction,
                        command="survey",
                        status="step",
                        result=result_payload
                    )
                    logger.info(f"[Channel {channel_id}] - Webhook sending result for survey step: success={success}, data={data}")

                    logger.debug(f"Webhook response for survey step: success={success}, data={data}")
                    try:
                    flag = (data or {}).get("survey")
                    logger.debug(f"Webhook response for decline step: success={success}, data={data}")
                    if flag == "continue":
                        logger.debug(f"[Channel {channel_id}] - Advancing and continuing survey (decline)")
                        state.next_step()
                        if view.continue_survey_func:
                            await view.continue_survey_func(interaction.channel, state)
                    elif flag == "end":
                        logger.debug(f"[Channel {channel_id}] - Advancing and finishing survey (decline)")
                        state.next_step()
                        from discord_bot.commands.survey import finish_survey as _finish
                        await _finish(view.bot_instance, interaction.channel, state)
                    elif flag == "cancel":
                        logger.debug(f"[Channel {channel_id}] - Cancelling survey per n8n instruction (decline)")
                        survey_manager.remove_survey(str(interaction.channel.id))
                    else:
                        logger.debug(f"[Channel {channel_id}] - No flag; default continue path (decline)")
                        state.next_step()
                        if view.continue_survey_func:
                            await view.continue_survey_func(interaction.channel, state)
                    except Exception as e:
                        logger.error(f"[Channel {channel_id}] - Error in state.next_step(): {e}", exc_info=True)
                    try:
                        logger.debug(f"[Channel {channel_id}] - Calling continue_survey_func for channel {getattr(interaction.channel, 'id', None)} and state {state}")
                        if view.continue_survey_func:
                            await view.continue_survey_func(interaction.channel, state)
                        else:
                            logger.warning(f"[Channel {channel_id}] - continue_survey_func is None, cannot call.")
                    except Exception as e:
                        logger.error(f"[Channel {channel_id}] - Error in continue_survey_func: {e}", exc_info=True)

                    if not success:
                        logger.error(f"Failed to send webhook for survey step: {view.cmd_or_step}")
                        if view.command_msg:
                            await view.command_msg.remove_reaction(Strings.PROCESSING, interaction.client.user)
                            error_msg = Strings.DAYOFF_ERROR.format(
                                days="Відмова від вихідних",
                                error=Strings.GENERAL_ERROR
                            )
                            await view.command_msg.edit(content=error_msg)
                            await view.command_msg.add_reaction(Strings.ERROR)
                        return

                    state.results[view.cmd_or_step] = ["Nothing"]
                    logger.info(f"Updated survey results: {state.results}")

                    if view.command_msg:
                        try:
                            await view.command_msg.remove_reaction(Strings.PROCESSING, interaction.client.user)
                            output_content = data.get("output", "Дякую! Не плануєш вихідні.") if data else "Дякую! Не плануєш вихідні."
                            await view.command_msg.edit(content=output_content, view=None, attachments=[])
                            logger.info(f"[Channel {channel_id}] - Updated command message {view.command_msg.id} with response")
                        except Exception as edit_error:
                            logger.error(f"[Channel {channel_id}] - Error editing command message {getattr(view.command_msg, 'id', 'N/A')}: {edit_error}", exc_info=True)

                    logger.info(f"Survey state before continuation - current step: {state.current_step()}, results: {state.results}")

                    if not state or not state.user_id:
                        logger.error("Invalid survey state for continuation")
                        return

                else:
                    logger.warning(f"[Channel {channel_id}] - No active survey state found for user in decline button callback. Treating as non-survey command or expired survey.")

                    if view.has_survey:
                        logger.error(f"[Channel {channel_id}] - Survey initiated but state not found in callback for step {view.cmd_or_step}.")
                        try:
                            if interaction.response.is_done():
                                logger.debug(f"[Channel {channel_id}] - interaction.response.is_done()=True, using followup.send for expired survey")
                                await interaction.followup.send(Strings.SURVEY_EXPIRED_OR_NOT_FOUND, ephemeral=True)
                            else:
                                logger.debug(f"[Channel {channel_id}] - interaction.response.is_done()=False, using response.send_message for expired survey")
                                await interaction.response.send_message(Strings.SURVEY_EXPIRED_OR_NOT_FOUND, ephemeral=True)
                        except Exception as e:
                            logger.error(f"[Channel {channel_id}] - Failed to send survey expired message: {e}")

                        if view.buttons_msg:
                            try:
                                await view.buttons_msg.delete()
                            except Exception as e:
                                logger.warning(f"[Channel {channel_id}] - Failed to delete buttons message after expired survey message: {e}")

                    else:
                        logger.error(f"[Channel {channel_id}] - Decline button clicked in non-survey context (has_survey=False) for command: {view.cmd_or_step}. No active survey state found.")
                        if view.command_msg:
                            try:
                                await view.command_msg.edit(content=Strings.GENERAL_ERROR, view=None)
                            except Exception as e:
                                logger.error(f"[Channel {channel_id}] - Error editing command message with general error: {e}")
                        if view.buttons_msg:
                            try:
                                await view.buttons_msg.delete()
                            except Exception as e:
                                logger.error(f"[Channel {channel_id}] - Error deleting buttons message: {e}")
                        view.stop()
            except Exception as e:
                session_id_for_log = view.session_id.split('_')[0] if view and view.session_id else 'N/A'
                logger.error(f"[Channel {session_id_for_log}] - Error in decline button callback: {e}", exc_info=True)
                if view and view.command_msg:
                    await view.command_msg.remove_reaction(Strings.PROCESSING, interaction.client.user)
                    error_msg = Strings.DAYOFF_ERROR.format(
                        days="Відмова від вихідних",
                        error=Strings.UNEXPECTED_ERROR
                    )
                    await view.command_msg.edit(content=error_msg)
                    await view.command_msg.add_reaction(Strings.ERROR)
                logger.error(f"[Channel {session_id_for_log}] - Failed to send error response in decline callback: {e}")
            finally:
                if view and view.buttons_msg:
                    try:
                        await view.buttons_msg.delete()
                        session_id_for_log = view.session_id.split('_')[0] if view and view.session_id else 'N/A'
                        logger.info(f"[Channel {session_id_for_log}] - Successfully deleted buttons message in finally block.")
                        view.stop()
                    except discord.NotFound:
                        session_id_for_log = view.session_id.split('_')[0] if view and view.session_id else 'N/A'
                        logger.warning(f"[Channel {session_id_for_log}] - Buttons message already deleted or not found in finally block.")
                    except Exception as e:
                        session_id_for_log = view.session_id.split('_')[0] if view and view.session_id else 'N/A'
                        logger.error(f"[Channel {session_id_for_log}] - Error deleting buttons message in finally block: {e}", exc_info=True)
    
def create_day_off_view(
    bot_instance,
    cmd_or_step: str,
    user_id: str,
    has_survey: bool = False,
    continue_survey_func=None,
    survey=None,
    session_id: Optional[str] = None,
    command_msg: Optional[discord.Message] = None,
    buttons_msg: Optional[discord.Message] = None
):
    """Creates a DayOffView_survey with buttons for each day of the week."""
    logger.info(f"[Channel {survey.session_id.split('_')[0] if survey and survey.session_id else 'N/A'}] - create_day_off_view called with cmd: {cmd_or_step}, user_id: {user_id}, has_survey: {has_survey}")
    # Use survey's session_id if available
    effective_session_id = session_id or (survey.session_id if survey else None)
    view = DayOffView_survey(
        bot_instance,
        cmd_or_step,
        user_id,
        has_survey,
        continue_survey_func,
        survey,
        session_id=effective_session_id
    )
    logger.debug(f"[Channel {view.session_id.split('_')[0]}] - DayOffView_survey instantiated successfully")
    view.command_msg = command_msg
    view.buttons_msg = buttons_msg

    days = [
        "Понеділок",
        "Вівторок",
        "Середа",
        "Четвер",
        "П'ятниця",
    ]

    for day in days:
        date_to_show = view.get_date_for_day(day)
        if date_to_show is None:
            continue
        button = DayOffButton_survey(
            label=day,
            custom_id=f"day_off_{day.lower()}_{user_id}",
            cmd_or_step=cmd_or_step,
        )
        view.add_item(button)

    view.add_item(ConfirmButton_survey())
    view.add_item(DeclineButton_survey())

    logger.debug(f"[Channel {view.session_id.split('_')[0]}] - Returning day off view")
    return view
