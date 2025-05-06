import discord
from typing import Optional
from config import logger, Strings, constants # Added Strings, constants
from services import webhook_service, survey_manager

class WorkloadView_survey(discord.ui.View):
    """View for workload selection - only used for non-survey commands"""
    def __init__(self, cmd_or_step: str, user_id: str, has_survey: bool = False, continue_survey_func=None):
        logger.debug(f"[{user_id}] - WorkloadView_survey.__init__ called for cmd_or_step: {cmd_or_step}, has_survey: {has_survey}")
        self.continue_survey_func = continue_survey_func # Add this line
        # Use configured timeout from constants
        super().__init__(timeout=constants.VIEW_CONFIGS[constants.ViewType.DYNAMIC]["timeout"])
        logger.debug(f"[{user_id}] - WorkloadView_survey initialized with timeout: {self.timeout}") # Added log
        self.cmd_or_step = cmd_or_step
        self.user_id = user_id
        self.has_survey = has_survey
        self.command_msg = None  # Reference to the command message
        self.buttons_msg = None  # Reference to the buttons message
        logger.debug(f"[{self.user_id}] - WorkloadView_survey initialized. command_msg: {self.command_msg}, buttons_msg: {self.buttons_msg}") # Added log

    async def on_timeout(self):
        logger.warning(f"WorkloadView_survey timed out for user {self.user_id}")

class WorkloadButton_survey(discord.ui.Button):
    def __init__(self, *, label: str, custom_id: str, cmd_or_step: str, continue_survey_func=None):
        super().__init__(
            style=discord.ButtonStyle.secondary,
            label=label,
            custom_id=custom_id
        )
        self.cmd_or_step = cmd_or_step
        self.continue_survey_func = continue_survey_func # Add this line

    async def _safe_defer_response(self, interaction, user_id):
        logger.debug(f"[{user_id}] - [DEBUG] Entering _safe_defer_response")
        logger.debug(f"[{user_id}] - Interaction response state: is_done={interaction.response.is_done()}")
        
        if not interaction.response.is_done():
            logger.info(f"[{user_id}] - Deferring interaction response (not done)")
            await interaction.response.defer(ephemeral=False)
            logger.debug(f"[{user_id}] - Successfully deferred")
        else:
            logger.warning(f"[{user_id}] - Interaction response already completed")
        
        logger.debug(f"[{user_id}] - [DEBUG] Exiting _safe_defer_response")

    async def callback(self, interaction: discord.Interaction):
        # Extra debug for connects_thisweek step
        logger.info(f"WorkloadButton_survey.callback entered. Interaction ID: {interaction.id}, Custom ID: {self.custom_id}")
        logger.debug(f"Button callback for step: {self.cmd_or_step}, interaction.response.is_done(): {interaction.response.is_done()}")
        from config import Strings # Import Strings locally
        """Handle button press with complete validation"""
        # Log entry with full interaction details
        logger.info(f"WorkloadButton_survey callback started - interaction: {interaction.id}, user: {getattr(interaction, 'user', None)}, bot: {getattr(interaction.client, 'user', None)}")

        # Detailed interaction validation
        if not interaction:
            logger.error("Null interaction received in callback")
            return

        view = None # Initialize view to None
        try:
            # Skip validation for bot's own messages
            if getattr(interaction.user, 'bot', False) and str(interaction.user.id) == str(interaction.client.user.id):
                logger.info("Processing bot's own interaction - skipping strict validation")
                view = self.view
                if not view or not isinstance(view, WorkloadView_survey):
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
                if not hasattr(self, 'view') or not isinstance(self.view, WorkloadView_survey):
                    logger.error("Invalid view in button callback")
                    return

                view = self.view
                if not hasattr(view, 'user_id') or not view.user_id:
                    logger.error("Invalid view - missing user_id")
                    return

        except Exception as e:
            logger.error(f"Error in WorkloadButton_survey callback: {str(e)}")
            return

            # Defer response to prevent timeout
            logger.debug(f"[{view.user_id}] - Attempting to defer interaction response")
            if not interaction.response.is_done():
                await interaction.response.defer(ephemeral=False)
            logger.debug(f"[{view.user_id}] - Interaction response deferred")

            logger.info(f"Processing workload selection for user {view.user_id}")

        except Exception as e:
            logger.error(f"Error in WorkloadButton_survey callback: {str(e)}")
            return

        try:
            # Ensure we have a valid view
            if not hasattr(self, 'view') or not isinstance(self.view, WorkloadView_survey):
                return

            view = self.view
            logger.debug(f"[{view.user_id}] - [DEBUG] Pre-deferral check at line 106")
            if not interaction.response.is_done():
                await self._safe_defer_response(interaction, getattr(view, 'user_id', 'unknown'))
            else:
                logger.warning(f"[{view.user_id}] - Skipping deferral at line 106 (already deferred)")

        except Exception as e:
            logger.error(f"Interaction handling failed: {e}")
            return

        if not hasattr(self, 'view') or not isinstance(self.view, WorkloadView_survey):
            logger.error(f"Invalid view in callback: {getattr(self, 'view', None)}")
            return

        view = self.view
        logger.info(f"Processing WorkloadView_survey callback - view user: {view.user_id}, interaction user: {interaction.user.id}")

        try: # Main try block to ensure button message deletion in finally
            if isinstance(view, WorkloadView_survey):
                # First, acknowledge the interaction to prevent timeout
                try:
                    logger.debug(f"[{view.user_id}] - Attempting to defer interaction response (second check)")
                    logger.debug(f"[{view.user_id}] - [DEBUG] Pre-deferral check at line 123")
                    if not interaction.response.is_done():
                        await self._safe_defer_response(interaction, view.user_id)
                    else:
                        logger.warning(f"[{view.user_id}] - Skipping deferral at line 123 (already deferred)")
                    logger.debug(f"[{view.user_id}] - Interaction response deferred (second check)")
                except Exception as e:
                    logger.error(f"[{view.user_id}] - Interaction response error: {e}")
                    return

                logger.info(f"Workload button clicked: {self.label} by user {view.user_id} for step {view.cmd_or_step}")

                # Add processing reaction to command message
                if view.command_msg:
                    try:
                        logger.debug(f"[{view.user_id}] - Attempting to add processing reaction to command message {view.command_msg.id}")
                        await view.command_msg.add_reaction(Strings.PROCESSING)
                        logger.info(f"[{view.user_id}] - Added processing reaction to command message {view.command_msg.id}")
                    except Exception as e:
                        logger.error(f"[{view.user_id}] - Error adding processing reaction to command message {getattr(view.command_msg, 'id', 'N/A')}: {e}", exc_info=True) # Added exc_info and safe access

                try:
                    # Set value based on button label and convert to integer
                    # Handle "Нічого немає" button specifically
                    if self.label == "Нічого немає":
                        if not interaction or not interaction.channel:
                            logger.error("Missing interaction data for Нічого немає button")
                            return
                        value = 0
                        logger.info(f"Нічого немає selected in channel {interaction.channel.id}")
                    else:
                        value = int(self.label)
                    logger.info(f"Parsed value: {value} from label: {self.label}")
                except ValueError:
                    logger.error(f"[{view.user_id}] - Could not convert button label to integer: {self.label}", exc_info=True)
                    # Handle the error, perhaps send an ephemeral message to the user
                    if not interaction.response.is_done():
                         await interaction.followup.send("Invalid button value.", ephemeral=True)
                    return # Exit callback if value is invalid
                except Exception as e:
                    logger.error(f"[{view.user_id}] - Unexpected error parsing button value: {e}", exc_info=True)
                    if not interaction.response.is_done():
                         await interaction.followup.send("An unexpected error occurred.", ephemeral=True)
                    return # Exit callback on unexpected error


                # Log right before the survey check
                logger.info(f"[{view.user_id}] - Checking view.has_survey in callback. Value: {view.has_survey}. Interaction ID: {interaction.id}")
                # Check if a survey exists for this user
                try:
                    logger.debug(f"[{view.user_id}] - Attempting to get survey state for user {view.user_id}.") # Added log
                    state = survey_manager.get_survey(view.user_id)
                    logger.debug(f"[{view.user_id}] - survey_manager.get_survey returned: {state}.") # Added log
                except Exception as e:
                    logger.error(f"[{view.user_id}] - Error getting survey state: {e}", exc_info=True) # Added error handling
                    # If getting survey state fails, we cannot proceed with the survey flow.
                    # Log the error and return.
                    return

                # Removed log: logger.info(f"[{view.user_id}] - Result of survey_manager.get_survey in callback: {state}. Interaction ID: {interaction.id}")

                # Delete buttons message FIRST as per user request
                logger.info(f"[{view.user_id}] - Attempting to delete buttons message before sending webhook.") # Added log
                if view.buttons_msg:
                    logger.debug(f"[{view.user_id}] - Type of view.buttons_msg: {type(view.buttons_msg)}") # Added log
                    try:
                        logger.info(f"[{view.user_id}] - Attempting to delete buttons message ID: {view.buttons_msg.id}")
                        await view.buttons_msg.delete()
                        logger.info(f"[{view.user_id}] - Successfully deleted buttons message ID: {view.buttons_msg.id}")
                        view.buttons_msg = None # Clear reference after deletion
                    except discord.NotFound:
                        logger.warning(f"[{view.user_id}] - Buttons message {getattr(view.buttons_msg, 'id', 'N/A')} already deleted or not found.")
                        view.buttons_msg = None # Clear reference if not found
                    except Exception as delete_error:
                        logger.error(f"[{view.user_id}] - Error deleting buttons message {getattr(view.buttons_msg, 'id', 'N/A')}: {delete_error}", exc_info=True)
                else:
                    logger.warning(f"[{view.user_id}] - view.buttons_msg is None or False, cannot delete.")

                if state: # Proceed if a survey state is found
                    logger.info(f"[{view.user_id}] - Processing as survey step for user {view.user_id}. Survey state found.") # Modified log
                    logger.debug(f"[{view.user_id}] - Entered survey state processing block.") # Added log
                    # Dynamic survey flow
                    # The redundant check 'if not state:' is removed as it's covered by the outer 'if state:'
                    # Removed temporary debug ephemeral message
                    # try:
                    #     logger.debug(f"[{view.user_id}] - Attempting to send debug ephemeral message.") # Added log
                    #     await interaction.followup.send("Debug: Survey state found.", ephemeral=True)
                    #     logger.debug(f"[{view.user_id}] - Debug ephemeral message sent successfully.") # Added log
                    # except Exception as e:
                    #     logger.error(f"[{view.user_id}] - Failed to send debug message (survey found): {e}", exc_info=True) # Added exc_info
                    logger.info(f"Found survey for user {view.user_id}, current step: {state.current_step()}")

                    # Send webhook for survey step
                    result_payload = {
                        "stepName": view.cmd_or_step,
                        "value": value
                    }
                    logger.info(f"[{view.user_id}] - Sending webhook for survey step: {view.cmd_or_step} with value: {value}")
                    logger.debug(f"[{view.user_id}] - Attempting webhook_service.send_webhook...") # Added log before webhook call
                    success, data = await webhook_service.send_webhook(
                        interaction,
                        command="survey",
                        status="step",
                        result=result_payload
                    )
                    logger.debug(f"[{view.user_id}] - webhook_service.send_webhook completed.") # Added log after successful webhook call
                    logger.info(f"[{view.user_id}] - Webhook sending result for survey step: success={success}, data={data}")

                    logger.info(f"Webhook response for survey step: success={success}, data={data}")
                    try:
                        logger.info(f"[{view.user_id}] - Calling state.next_step()")
                        state.next_step()
                    except Exception as e:
                        logger.error(f"[{view.user_id}] - Error in state.next_step(): {e}", exc_info=True)
                    try:
                        logger.info(f"[{view.user_id}] - Calling continue_survey_func for channel {getattr(interaction.channel, 'id', None)} and state {state}")
                        await self.continue_survey_func(interaction.channel, state)
                    except Exception as e:
                        logger.error(f"[{view.user_id}] - Error in continue_survey_func: {e}", exc_info=True)

                    if not success:
                        logger.error(f"Failed to send webhook for survey step: {view.cmd_or_step}")
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
                    state.results[view.cmd_or_step] = value
                    logger.info(f"Updated survey results: {state.results}")
                    
                    # Update command message with response
                    if view.command_msg:
                        # Clear all reactions except ❌
                        for reaction in view.command_msg.reactions:
                            if str(reaction.emoji) != "❌":
                                await reaction.remove(interaction.client.user)
                        if "output" in data and data["output"].strip():
                            logger.debug(f"[{view.user_id}] - Attempting to edit command message with output: {data['output']}")
                            await view.command_msg.edit(content=data["output"])
                        else:
                            logger.debug(f"[{view.user_id}] - Attempting to edit command message with default success message")
                            await view.command_msg.edit(content=f"Дякую! Навантаження: {value} годин записано.")
                        logger.info(f"[{view.user_id}] - Updated command message with response")

                    # Log survey state before continuation
                    logger.info(f"Survey state before continuation - current step: {state.current_step()}, results: {state.results}")
                    
                    # Let n8n handle the survey continuation through webhook response
                    # Don't advance the step here, as it will be handled by the webhook service
                    # But verify we have a valid state for continuation
                    if not state or not state.user_id:
                        logger.error("Invalid survey state for continuation")
                        return

                    logger.info(f"[{view.user_id}] - Webhook successful, checking for survey continuation logic.") # Added log

                else: # If survey state is not found
                    logger.warning(f"[{view.user_id}] - No active survey state found for user in workload button callback. Treating as non-survey command or expired survey.")
                    # Removed temporary debug ephemeral message
                    # try:
                    #     logger.debug(f"[{view.user_id}] - Attempting to send debug ephemeral message (survey not found).") # Added log
                    #     await interaction.followup.send("Debug: Survey state NOT found.", ephemeral=True)
                    #     logger.debug(f"[{view.user_id}] - Debug ephemeral message (survey not found) sent successfully.") # Added log
                    # except Exception as e:
                    #     logger.error(f"[{view.user_id}] - Failed to send debug message (survey not found): {e}", exc_info=True) # Added exc_info

                    # Check if it was intended to be a survey step but the survey is missing
                    if view.has_survey: # This indicates it was initiated as a survey step
                         logger.error(f"[{view.user_id}] - Survey initiated but state not found in callback for step {view.cmd_or_step}.")
                         # Inform the user that the survey might have expired
                         try:
                             # Use followup if interaction was deferred
                             if interaction.response.is_done():
                                 logger.debug(f"[{view.user_id}] - interaction.response.is_done()=True, using followup.send for expired survey")
                                 await interaction.followup.send(Strings.SURVEY_EXPIRED_OR_NOT_FOUND, ephemeral=True)
                             else:
                                 logger.debug(f"[{view.user_id}] - interaction.response.is_done()=False, using response.send_message for expired survey")
                                 await interaction.response.send_message(Strings.SURVEY_EXPIRED_OR_NOT_FOUND, ephemeral=True)
                         except Exception as e:
                             logger.error(f"[{view.user_id}] - Failed to send survey expired message: {e}")

                         # Attempt to clean up the buttons message
                         if view.buttons_msg:
                             try:
                                 await view.buttons_msg.delete()
                             except Exception as e:
                                 logger.warning(f"[{view.user_id}] - Failed to delete buttons message after expired survey message: {e}")

                    else: # Original else block for non-survey commands
                        logger.info(f"[{view.user_id}] - Processing as regular command: {view.cmd_or_step}")
                        # Regular slash command
                        webhook_payload = {
                            "command": view.cmd_or_step,
                            "status": "ok",
                            "result": {"workload": value}
                        }
                        logger.debug(f"[{view.user_id}] - Preparing to send webhook for regular command. Payload: {webhook_payload}")

                        # Delete buttons message FIRST as per user request
                        if view.buttons_msg:
                            logger.debug(f"[{view.user_id}] - Attempting to delete buttons message")
                            await view.buttons_msg.delete()
                            logger.info(f"[{view.user_id}] - Deleted buttons message")

                        logger.debug(f"[{view.user_id}] - Attempting to send webhook for command: {view.cmd_or_step}")
                        success, data = await webhook_service.send_webhook(
                            interaction,
                            command=webhook_payload["command"],
                            status=webhook_payload["status"],
                            result=webhook_payload["result"]
                        )
                        logger.info(f"[{view.user_id}] - Webhook response for command: success={success}, data={data}")
                        logger.info(f"[{view.user_id}] - Webhook response for command: success={success}, data={data}")

                        if success and data and "output" in data:
                            # Update command message with success
                            if view.command_msg:
                                logger.debug(f"[{view.user_id}] - Attempting to remove processing reaction from command message")
                                await view.command_msg.remove_reaction(Strings.PROCESSING, interaction.client.user)
                                logger.debug(f"[{view.user_id}] - Attempting to edit command message with success output: {data['output']}")
                                await view.command_msg.edit(content=data["output"])
                                logger.info(f"[{view.user_id}] - Updated command message with success: {data['output']}")

                            # Delete buttons message
                            if view.buttons_msg:
                                logger.debug(f"[{view.user_id}] - Attempting to delete buttons message")
                                await view.buttons_msg.delete()
                                logger.info(f"[{view.user_id}] - Deleted buttons message")
                        else:
                            logger.error(f"Failed to send webhook for command: {view.cmd_or_step}")
                            if view.command_msg:
                                await view.command_msg.remove_reaction(Strings.PROCESSING, interaction.client.user)
                                error_msg = Strings.WORKLOAD_ERROR.format(
                                    hours=value,
                                    error=Strings.GENERAL_ERROR
                                )
                                await view.command_msg.edit(content=error_msg)
                                await view.command_msg.add_reaction(Strings.ERROR)
                            if view.buttons_msg:
                                if view.buttons_msg:
                                    try:
                                        await view.buttons_msg.delete()
                                    except discord.NotFound:
                                        logger.debug("Buttons message already deleted")

        except Exception as e:
            logger.error(f"[{view.user_id}] - Error in workload button callback: {e}", exc_info=True) # Modified log to include user_id and exc_info
            if view and view.command_msg: # Check if view and command_msg exist before accessing
                await view.command_msg.remove_reaction(Strings.PROCESSING, interaction.client.user)
                value = 0 if self.label == "Нічого немає" else self.label
                error_msg = Strings.WORKLOAD_ERROR.format(
                    hours=value,
                    error=Strings.UNEXPECTED_ERROR
                )
                await view.command_msg.edit(content=error_msg)
                await view.command_msg.add_reaction(Strings.ERROR)
            logger.error(f"[{view.user_id}] - Failed to send error response in workload callback: {e}") # Modified log to include user_id
        finally:
            # Ensure buttons message is deleted in all cases
            if view and view.buttons_msg: # Check if view and buttons_msg exist before accessing
                logger.debug(f"[{view.user_id}] - Attempting to delete buttons message in finally block.")
                try:
                    await view.buttons_msg.delete()
                    logger.info(f"[{view.user_id}] - Successfully deleted buttons message in finally block.")
                except discord.NotFound:
                    logger.warning(f"[{view.user_id}] - Buttons message already deleted or not found in finally block.")
                except Exception as e:
                    logger.error(f"[{view.user_id}] - Error deleting buttons message in finally block: {e}", exc_info=True)


def create_workload_view(cmd: str, user_id: str, timeout: Optional[float] = None, has_survey: bool = False, continue_survey_func=None) -> WorkloadView_survey:
    """Create workload view for regular commands only"""
    print(f"[{user_id}] - create_workload_view function entered")
    logger.debug(f"[{user_id}] - create_workload_view called with cmd: {cmd}, user_id: {user_id}, has_survey: {has_survey}")
    try:
        view = WorkloadView_survey(cmd, user_id, has_survey=has_survey, continue_survey_func=continue_survey_func)
        logger.debug(f"[{user_id}] - WorkloadView_survey instantiated successfully")
    except Exception as e:
        logger.error(f"[{user_id}] - Error instantiating WorkloadView_survey: {e}")
        raise # Re-raise the exception after logging

    logger.debug(f"[{user_id}] - Before importing WORKLOAD_OPTIONS")
    from config.constants import WORKLOAD_OPTIONS
    logger.debug(f"[{user_id}] - After importing WORKLOAD_OPTIONS. WORKLOAD_OPTIONS: {WORKLOAD_OPTIONS}")
    # Add all workload options as buttons, including "Нічого немає"
    try:
        # Only add buttons for workload-related commands
        logger.debug(f"[{user_id}] - Checking cmd: {cmd}") # Added log to check cmd value
        if cmd in ["workload_today", "workload_nextweek"]:
            for hour in WORKLOAD_OPTIONS:
                custom_id = f"workload_button_{hour}_{cmd}_{user_id}"
                button = WorkloadButton_survey(label=hour, custom_id=custom_id, cmd_or_step=cmd, continue_survey_func=view.continue_survey_func)
                logger.debug(f"[{user_id}] - Adding button with label: {hour}, custom_id: {custom_id}")
                view.add_item(button)
        logger.debug(f"[{user_id}] - Finished adding workload buttons")
    except Exception as e:
        logger.error(f"[{user_id}] - Error adding workload buttons: {e}")
        raise # Re-raise the exception after logging

    return view