import discord # type: ignore
from typing import Optional
from config import constants, Strings # Added Strings, constants
from services import webhook_service, survey_manager
from services.logging_utils import get_logger


def _log(step: str, *, user_id: str | None = None, channel_id: str | int | None = None, session_id: str | None = None):
    payload = {}
    if user_id is not None:
        payload["userId"] = str(user_id)
    if channel_id is not None:
        payload["channelId"] = str(channel_id)
    if session_id is not None:
        payload["sessionId"] = str(session_id)
    return get_logger(step, payload)

class WorkloadView_survey(discord.ui.View):
    """View for workload selection - only used for non-survey commands"""
    def __init__(self, cmd_or_step: str, user_id: str, has_survey: bool = False, continue_survey_func=None, survey=None, command_msg: Optional[discord.Message] = None, bot_instance=None, session_id: Optional[str] = None): # Added bot_instance and session_id
        self.session_id = session_id if session_id is not None else "" # Ensure session_id is always a string
        _log("view.workload_survey", session_id=self.session_id, user_id=user_id).debug(
            "__init__", extra={"cmd_or_step": cmd_or_step, "has_survey": has_survey}
        )
        self.continue_survey_func = continue_survey_func # Store continue survey function
        self.survey = survey # Store the survey object
        # Use configured timeout from constants
        super().__init__(timeout=constants.VIEW_CONFIGS[constants.ViewType.DYNAMIC]["timeout"]) # Set view timeout
        _log("view.workload_survey", session_id=self.session_id, user_id=user_id).debug(
            "initialized", extra={"timeout": self.timeout}
        )
        self.cmd_or_step = cmd_or_step
        self.user_id = user_id
        self.has_survey = has_survey
        self.command_msg = command_msg  # Reference to the command message
        self.buttons_msg: Optional[discord.Message] = None  # Reference to the buttons message
        self.bot_instance = bot_instance # Store bot instance
        _log("view.workload_survey", session_id=self.session_id, user_id=user_id).debug(
            "state", extra={"has_command_msg": bool(self.command_msg), "has_buttons_msg": bool(self.buttons_msg)}
        )

    async def on_timeout(self):
        _log("view.workload_survey", session_id=self.session_id, user_id=self.user_id).warning("timeout")
        # Clean up view first
        if self.buttons_msg:
            try:
                await self.buttons_msg.delete()
                _log("view.workload_survey", session_id=self.session_id, user_id=self.user_id).info("deleted buttons on timeout", extra={"buttons_msg_id": getattr(self.buttons_msg, 'id', None)})
            except discord.NotFound:
                _log("view.workload_survey", session_id=self.session_id, user_id=self.user_id).warning("buttons already deleted on timeout")
            except Exception as e:
                _log("view.workload_survey", session_id=self.session_id, user_id=self.user_id).exception("error deleting buttons on timeout")
            finally:
                self.buttons_msg = None
                self.stop()

        # Skip survey timeout handling if survey was already removed
        # This prevents duplicate cleanup and timeout messages
        if not survey_manager.get_survey_by_session(self.session_id):
            _log("view.workload_survey", session_id=self.session_id, user_id=self.user_id).info("survey removed; skip timeout handling")
            return

        # Handle survey timeout
        if self.has_survey and self.bot_instance and self.session_id:
            _log("view.workload_survey", session_id=self.session_id, user_id=self.user_id).info("calling handle_survey_incomplete")
            from discord_bot.commands.survey import handle_survey_incomplete # Import locally to avoid circular dependency
            await handle_survey_incomplete(self.bot_instance, self.session_id)
        else:
            _log("view.workload_survey", session_id=self.session_id, user_id=self.user_id).warning("cannot call handle_survey_incomplete", extra={"has_survey": self.has_survey, "has_bot": bool(self.bot_instance)})

class WorkloadButton_survey(discord.ui.Button):
    def __init__(self, *, label: str, custom_id: str, cmd_or_step: str, continue_survey_func=None):
        super().__init__(
            style=discord.ButtonStyle.secondary,
            label=label,
            custom_id=custom_id
        )
        self.cmd_or_step = cmd_or_step
        self.continue_survey_func = continue_survey_func # Add this line


    async def callback(self, interaction: discord.Interaction):
        ch_id = getattr(getattr(interaction, "channel", None), "id", None)
        u_id = getattr(getattr(interaction, "user", None), "id", None)
        log = _log("view.workload_survey", channel_id=ch_id, user_id=str(u_id) if u_id else None)
        log.debug("callback entered", extra={"interaction_id": getattr(interaction, "id", None), "custom_id": self.custom_id})
        log.debug("button callback", extra={"step": self.cmd_or_step, "is_done": getattr(getattr(interaction, "response", None), "is_done", lambda: None)() if getattr(interaction, "response", None) else None})

        """Handle button press with complete validation"""
        # Log entry with full interaction details
        log.info("callback started", extra={"interaction_id": getattr(interaction, "id", None)})

        # Detailed interaction validation
        if not interaction:
            log.error("null interaction")
            return

        view = None # Initialize view to None
        try:
            # Skip validation for bot's own messages
            if getattr(interaction.user, 'bot', False) and str(interaction.user.id) == str(interaction.client.user.id):
                logger.info("Processing bot's own interaction - skipping strict validation")
                view = self.view
                if not view or not isinstance(view, WorkloadView_survey): # Validate view type
                    logger.error("Invalid view for bot interaction")
                    return
            else:
                # Normal user validation
                required_attrs = ['response', 'user', 'channel', 'client']
                missing_attrs = [attr for attr in required_attrs
                                if not hasattr(interaction, attr)]

                if missing_attrs:
                    logger.error(f"Invalid interaction - missing: {missing_attrs}")
                    return

                # Validate view and survey state
                if not hasattr(self, 'view') or not isinstance(self.view, WorkloadView_survey): # Validate view type
                    logger.error("Invalid view in button callback")
                    return

                view = self.view # Get the parent view
                if not hasattr(view, 'user_id') or not view.user_id:
                    logger.error("Invalid view - missing user_id")
                    return

        except Exception as e:
            logger.error(f"Error in WorkloadButton_survey callback: {str(e)}")
            return

        # Defer response to prevent timeout (redundant block, removed)
        # logger.debug(f"[{view.user_id}] - Attempting to defer interaction response")
        # if not interaction.response.is_done():
        #     await interaction.response.defer(ephemeral=False)
        # logger.debug(f"[{view.user_id}] - Interaction response deferred")

        logger.info("Processing workload selection for channel {view.session_id.split('_')[0]}")

        try: # New main try block
            # Ensure we have a valid view
            if not hasattr(self, 'view') or not isinstance(self.view, WorkloadView_survey):
                return

            view = self.view # Get the parent view
            logger.info(f"Processing WorkloadView_survey callback - view user: {view.user_id}, interaction user: {interaction.user.id}")

            if isinstance(view, WorkloadView_survey):
                # Removed deferral calls as per user request.
                # If interaction is not responded to within 3 seconds, Discord will show "Interaction failed".

                logger.info(f"Workload button clicked: {self.label} by user {view.user_id} for step {view.cmd_or_step} in channel {view.session_id.split('_')[0]}")
                if view.command_msg: # Add check for None
                    try:
                        logger.debug(f"[Channel {view.session_id.split('_')[0]}] - Attempting to add processing reaction to command message {view.command_msg.id}")
                        await view.command_msg.add_reaction(Strings.PROCESSING)
                        logger.debug(f"[Channel {view.session_id.split('_')[0]}] - Added processing reaction to command message {view.command_msg.id}") # Change to DEBUG
                    except Exception as e:
                        logger.error(f"[Channel {view.session_id.split('_')[0]}] - Error adding processing reaction to command message {getattr(view.command_msg, 'id', 'N/A')}: {e}", exc_info=True) # Added exc_info and safe access

            try:
                # Set value based on button label and convert to integer
                # Handle "Нічого немає" button specifically
                if self.label == "Нічого немає":
                    if not interaction or not interaction.channel:
                        logger.error("Missing interaction data for Нічого немає button")
                        return
                    value = 0
                    logger.debug(f"Нічого немає selected in channel {interaction.channel.id}") # Change to DEBUG
                else:
                    value = int(self.label)
                logger.debug(f"Parsed value: {value} from label: {self.label}") # Change to DEBUG
            except ValueError:
                logger.error(f"[Channel {view.session_id.split('_')[0]}] - Could not convert button label to integer: {self.label}", exc_info=True)
                # Handle the error, perhaps send an ephemeral message to the user
                if not interaction.response.is_done():
                     await interaction.followup.send("Invalid button value.", ephemeral=True)
                return # Exit callback if value is invalid
            except Exception as e:
                logger.error(f"[Channel {view.session_id.split('_')[0]}] - Unexpected error parsing button value: {e}", exc_info=True)
                if not interaction.response.is_done():
                     await interaction.followup.send("An unexpected error occurred.", ephemeral=True)
                return # Exit callback on unexpected error


            # Log right before the survey check
            # Check if a survey exists for this channel
            try: # Get survey state
                state = survey_manager.get_survey(str(interaction.channel.id)) # Get by channel_id
                _log("view.workload_survey", session_id=getattr(view, 'session_id', None), user_id=getattr(view, 'user_id', None)).debug("survey lookup", extra={"found": bool(state)})
            except Exception as e:
                _log("view.workload_survey", session_id=getattr(view, 'session_id', None), user_id=getattr(view, 'user_id', None)).exception("error getting survey state")
                # If getting survey state fails, we cannot proceed with the survey flow.
                # Log the error and return.
                return

            # Removed log: logger.info(f"[{view.user_id}] - Result of survey_manager.get_survey in callback: {state}. Interaction ID: {interaction.id}")

            # Delete buttons message FIRST as per user request
            if view.buttons_msg:
                try:
                    await view.buttons_msg.delete()
                    _log("view.workload_survey", session_id=getattr(view, 'session_id', None), user_id=getattr(view, 'user_id', None)).info("deleted buttons message")
                    view.buttons_msg = None # Clear reference after successful deletion
                    view.stop() # Stop the view since buttons are gone
                except discord.NotFound:
                    _log("view.workload_survey", session_id=getattr(view, 'session_id', None), user_id=getattr(view, 'user_id', None)).warning("buttons already deleted or not found")
                    view.buttons_msg = None # Clear reference if not found
                except Exception as delete_error:
                    _log("view.workload_survey", session_id=getattr(view, 'session_id', None), user_id=getattr(view, 'user_id', None)).exception("error deleting buttons message")
            else:
                logger.warning(f"[Channel {view.session_id.split('_')[0]}] - view.buttons_msg is None or False, cannot delete.")

            if state: # Proceed if a survey state is found
                _log("view.workload_survey", session_id=getattr(view, 'session_id', None), user_id=getattr(view, 'user_id', None)).info("found survey", extra={"current_step": state.current_step() if state else None})

                # Send webhook for survey step
                result_payload = {
                    "stepName": view.cmd_or_step, # Include step name
                    "value": value
                }
                _log("view.workload_survey", session_id=getattr(view, 'session_id', None), user_id=getattr(view, 'user_id', None)).info("sending survey webhook", extra={"step": view.cmd_or_step, "value": value})
                success, data = await webhook_service.send_webhook(
                    interaction,
                    command="survey",
                    status="step",
                    result=result_payload
                )
                _log("view.workload_survey", session_id=getattr(view, 'session_id', None), user_id=getattr(view, 'user_id', None)).info("survey webhook result", extra={"success": success})

                log.debug("survey webhook response", extra={"success": success})
                # Decide continuation based on n8n response flag via helper
                from discord_bot.commands.survey import process_survey_flag, finish_survey as _finish
                flag = (data or {}).get("survey")
                try:
                    await process_survey_flag(
                        interaction.channel,
                        state,
                        flag,
                        self.continue_survey_func,
                        lambda ch, s: _finish(interaction.client, ch, s),
                    )
                except Exception as e:
                    _log("view.workload_survey", session_id=getattr(view, 'session_id', None), user_id=getattr(view, 'user_id', None)).exception("error handling survey flow after webhook")

                if not success:
                    _log("view.workload_survey", session_id=getattr(view, 'session_id', None), user_id=getattr(view, 'user_id', None)).error("failed to send survey webhook", extra={"step": view.cmd_or_step})
                    if view.command_msg:
                        await view.command_msg.remove_reaction(Strings.PROCESSING, interaction.client.user)
                        error_msg = Strings.WORKLOAD_ERROR.format(
                            hours=value,
                            error=Strings.GENERAL_ERROR
                        )
                        await view.command_msg.edit(content=error_msg)
                        await view.command_msg.add_reaction(Strings.ERROR)
                    # The buttons message is already attempted to be deleted above
                    return

                # Update survey state
                # Record result through manager to consolidate writes
                survey_manager.record_step_result(interaction.channel.id, view.cmd_or_step, value)
                _log("view.workload_survey", session_id=getattr(view, 'session_id', None), user_id=getattr(view, 'user_id', None)).info("updated survey results", extra={"step": view.cmd_or_step})

                # Update command message with n8n output instead of deleting it
                if view.command_msg:
                    try:
                        await view.command_msg.remove_reaction(Strings.PROCESSING, interaction.client.user)
                        output_content = data.get("output", f"Дякую! Робоче навантаження {value} годин записано.") if data else f"Дякую! Робоче навантаження {value} годин записано." # Default success message
                        await view.command_msg.edit(content=output_content, view=None, attachments=[]) # Update content and remove view/attachments
                        logger.info(f"[Channel {view.session_id.split('_')[0]}] - Updated command message {view.command_msg.id} with response")
                    except Exception as edit_error:
                        logger.error(f"[Channel {view.session_id.split('_')[0]}] - Error editing command message {getattr(view.command_msg, 'id', 'N/A')}: {edit_error}", exc_info=True)


                # Log survey state before continuation
                logger.info(f"Survey state before continuation - current step: {state.current_step()}, results: {state.results}")

                # Survey continuation is handled by continue_survey_func
                # Don't advance the step here, as it will be handled by the webhook service
                # But verify we have a valid state for continuation
                if not state or not state.user_id:
                    logger.error("Invalid survey state for continuation")
                    return


            else: # If survey state is not found
                logger.warning(f"[Channel {view.session_id.split('_')[0]}] - No active survey state found for user in workload button callback. Treating as non-survey command or expired survey.")

                if view.has_survey: # This indicates it was initiated as a survey step
                     logger.error(f"[Channel {view.session_id.split('_')[0]}] - Survey initiated but state not found in callback for step {view.cmd_or_step}.")
                     # Inform the user that the survey might have expired
                     try:
                         # Use followup if interaction was deferred
                         if interaction.response.is_done():
                             logger.debug(f"[Channel {view.session_id.split('_')[0]}] - interaction.response.is_done()=True, using followup.send for expired survey")
                             await interaction.followup.send(Strings.SURVEY_EXPIRED_OR_NOT_FOUND, ephemeral=True)
                         else:
                             logger.debug(f"[Channel {view.session_id.split('_')[0]}] - interaction.response.is_done()=False, using response.send_message for expired survey")
                             await interaction.response.send_message(Strings.SURVEY_EXPIRED_OR_NOT_FOUND, ephemeral=True)
                     except Exception as e:
                         logger.error(f"[Channel {view.session_id.split('_')[0]}] - Failed to send survey expired message: {e}")

                     # Attempt to clean up the buttons message
                     if view.buttons_msg:
                         try:
                             await view.buttons_msg.delete()
                         except Exception as e:
                             logger.warning(f"[Channel {view.session_id.split('_')[0]}] - Failed to delete buttons message after expired survey message: {e}")

                else: # Handle the case where has_survey is False and state is not found
                    logger.error(f"[Channel {view.session_id.split('_')[0]}] - Workload button clicked in non-survey context (has_survey=False) for command: {view.cmd_or_step}. No active survey state found.")
                    # Optionally, send a message to the user indicating an unexpected error
                    if view.command_msg:
                        try:
                            await view.command_msg.edit(content=Strings.GENERAL_ERROR, view=None)
                        except Exception as e:
                            logger.error(f"[Channel {view.session_id.split('_')[0]}] - Error editing command message with general error: {e}")
                    if view.buttons_msg:
                        try:
                            await view.buttons_msg.delete()
                        except Exception as e:
                            logger.error(f"[Channel {view.session_id.split('_')[0]}] - Error deleting buttons message: {e}")
                    view.stop() # Stop the view
        except Exception as e:
            logger.error(f"[Channel {view.session_id.split('_')[0]}] - Error in workload button callback: {e}", exc_info=True) # Modified log to include user_id and exc_info
            if view and view.command_msg: # Check if view and command_msg exist before accessing
                await view.command_msg.remove_reaction(Strings.PROCESSING, interaction.client.user)
                value = 0 if self.label == "Нічого немає" else self.label
                error_msg = Strings.WORKLOAD_ERROR.format(
                    hours=value,
                    error=Strings.UNEXPECTED_ERROR
                )
                await view.command_msg.edit(content=error_msg)
                await view.command_msg.add_reaction(Strings.ERROR)
            logger.error(f"[Channel {view.session_id.split('_')[0]}] - Failed to send error response in workload callback: {e}") # Modified log to include user_id
        finally:
            # Ensure buttons message is deleted in all cases
            if view and view.buttons_msg: # Check if view and buttons_msg exist before accessing
                try:
                    await view.buttons_msg.delete()
                    logger.info(f"[Channel {view.session_id.split('_')[0]}] - Successfully deleted buttons message in finally block.")
                    view.stop() # Stop the view since buttons are gone
                except discord.NotFound:
                    logger.warning(f"[Channel {view.session_id.split('_')[0]}] - Buttons message already deleted or not found in finally block.")
                except Exception as e:
                    logger.error(f"[Channel {view.session_id.split('_')[0]}] - Error deleting buttons message in finally block: {e}", exc_info=True)


def create_workload_view(bot_instance, cmd: str, user_id: str, timeout: Optional[float] = None, has_survey: bool = False, continue_survey_func=None, survey=None, command_msg: Optional[discord.Message] = None) -> WorkloadView_survey: # Added bot_instance parameter
    """Create workload view for regular commands only"""
    logger.info(f"[Channel {survey.session_id.split('_')[0] if survey and survey.session_id else 'N/A'}] - create_workload_view called with cmd: {cmd}, user_id: {user_id}, has_survey: {has_survey}") # Change to INFO
    view: Optional[WorkloadView_survey] = None # Initialize view to None
    try:
        view = WorkloadView_survey(cmd, user_id, has_survey=has_survey, continue_survey_func=continue_survey_func, survey=survey, command_msg=command_msg, bot_instance=bot_instance, session_id=survey.session_id if survey else None) # Pass bot_instance and session_id
        logger.debug(f"[Channel {view.session_id.split('_')[0]}] - WorkloadView_survey instantiated successfully") # Keep debug
    except Exception as e:
        logger.error(f"[Channel {view.session_id.split('_')[0] if view and view.session_id else 'N/A'}] - Error instantiating WorkloadView_survey: {e}")
        raise # Re-raise the exception after logging

    logger.debug(f"[Channel {view.session_id.split('_')[0]}] - Accessing WORKLOAD_OPTIONS from constants")
    # Add workload option buttons
    try:
        # Only add buttons for workload-related commands
        logger.debug(f"[Channel {view.session_id.split('_')[0]}] - Checking cmd: {cmd}") # Added log to check cmd value
        if cmd in ["workload_today", "workload_nextweek"]:
            for hour in constants.WORKLOAD_OPTIONS:
                custom_id = f"workload_button_{hour}_{cmd}_{user_id}"
                button = WorkloadButton_survey(label=hour, custom_id=custom_id, cmd_or_step=cmd, continue_survey_func=view.continue_survey_func) # Create button
                logger.debug(f"[Channel {view.session_id.split('_')[0]}] - Adding button with label: {hour}, custom_id: {custom_id}")
                view.add_item(button)
    except Exception as e:
        logger.error(f"[Channel {view.session_id.split('_')[0]}] - Error adding workload buttons: {e}")
        raise # Re-raise the exception after logging
    logger.debug(f"[Channel {view.session_id.split('_')[0]}] - Returning workload view") # Keep debug
    return view
