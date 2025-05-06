import asyncio
import discord
import json # Added for Notion ToDo JSON parsing
from typing import Optional, List, Any # Added Any
from config import ViewType, logger, Strings, Config, constants # Added constants
from services import survey_manager, webhook_service
from services.notion_todos import Notion_todos # Added for Notion ToDo fetching
from services.survey import SurveyFlow # Added import
# Removed factory import
from discord_bot.views.workload_survey import create_workload_view # Use survey-specific view
from bot import bot # Import the bot instance from the root bot.py

# ==================================
# Survey-Specific Modals
# ==================================

class ConnectsModal(discord.ui.Modal):
    """Modal specifically for handling the 'connects' step in the survey."""
    def __init__(self, survey: SurveyFlow, step_name: str):
        """Initializes the ConnectsModal."""
        try:
            logger.info(f"Initializing ConnectsModal for user {survey.user_id} step {step_name}")

            # Verify required survey properties
            if not survey.user_id or not survey.channel_id:
                raise ValueError("Survey missing required properties")

            # Initialize modal with title
            title = Strings.CONNECTS_MODAL
            super().__init__(title=title, timeout=300)
            logger.info("Modal base initialized")

            # Store survey data
            self.survey = survey
            self.step_name = step_name

            # Create and configure text input
            logger.info("Creating TextInput field")
            self.connects_input = discord.ui.TextInput(
                label=Strings.CONNECTS_INPUT,
                placeholder=Strings.CONNECTS_PLACEHOLDER,
                min_length=1,
                max_length=3,
                required=True,
                style=discord.TextStyle.short
            )

            # Add input to modal
            logger.info("Adding TextInput to modal")
            self.add_item(self.connects_input)

            logger.info("ConnectsModal initialization complete")

        except Exception as e:
            logger.error(f"Error initializing ConnectsModal: {e}", exc_info=True)
            raise

    async def on_submit(self, interaction: discord.Interaction):
        """Handles the modal submission for the connects step."""
        logger.info("DEBUG: Entered ConnectsModal.on_submit")
        logger.info("Starting ConnectsModal submission handling")

        async def send_error(message: str):
            """Helper to send error response"""
            try:
                if not interaction.response.is_done():
                    await interaction.response.send_message(message, ephemeral=True)
                else:
                    await interaction.followup.send(message, ephemeral=True)
            except Exception as e:
                logger.error(f"Failed to send error message: {e}")

        try:
            user_input = self.connects_input.value.strip()
            logger.info(f"Received connects input: {user_input}")

            # Validate input is a number and in reasonable range
            if not user_input.isdigit():
                logger.warning(f"Invalid connects input (non-digit): {user_input}")
                await send_error(Strings.NUMBER_REQUIRED)
                return

            connects = int(user_input)
            if connects < 0 or connects > 999:
                logger.warning(f"Invalid connects range: {connects}")
                await send_error(f"{Strings.NUMBER_REQUIRED}. Кількість коннектів має бути від 0 до 999")
                return

            # Handle interaction response
            if not interaction.response.is_done():
                await interaction.response.defer(ephemeral=True)
                logger.info("Deferred modal response")

            # Verify user and channel
            if str(interaction.user.id) != str(self.survey.user_id):
                logger.warning(f"Wrong user for connects modal: {interaction.user.id} vs {self.survey.user_id}")
                await send_error(Strings.NOT_YOUR_SURVEY)
                return

            if str(interaction.channel.id) != str(self.survey.channel_id):
                logger.warning(f"Wrong channel for connects modal: {interaction.channel.id} vs {self.survey.channel_id}")
                await send_error(Strings.WRONG_CHANNEL)
                return

            logger.info(f"Storing connects result: {connects}")
            # Store the validated result
            try:
                self.survey.add_result(self.step_name, str(connects))
                logger.info(f"After add_result, survey.results: {self.survey.results}")
            except Exception as e:
                logger.error(f"Error storing connects result: {e}")
                await send_error(Strings.GENERAL_ERROR)
                return

            logger.info("Cleaning up previous message")
            # Clean up previous message
            try:
                await cleanup_survey_message(interaction, self.survey)
            except Exception as e:
                logger.warning(f"Error cleaning up survey message: {e}")
                # Continue flow even if cleanup fails

            logger.info("Sending confirmation message")
            # Confirm submission
            # Only defer the reply to show "Bot thinking" (loading state), do not send a message
            # Already handled above if not interaction.response.is_done()

            logger.info("Advancing survey")
            # Advance survey
            try:
                self.survey.next_step()
                logger.info(f"Survey results after connects: {self.survey.results}")
                logger.info(f"Survey steps: {getattr(self.survey, 'steps', None)}")
                logger.info(f"Survey current_step: {self.survey.current_step() if hasattr(self.survey, 'current_step') else None}")
                logger.info(f"Survey is_done: {self.survey.is_done()}")
                if self.survey.is_done():
                    logger.info("Survey is complete, finishing")
                    await finish_survey(interaction.channel, self.survey)
                else:
                    logger.info("Survey continuing to next step")
                    # Send step webhook for just this step
                    try:
                        step_payload = {
                            "command": "survey",
                            "status": "step",
                            "message": "",
                            "result": {
                                "stepName": self.step_name,
                                "value": str(connects)
                            },
                            "userId": str(self.survey.user_id),
                            "channelId": str(self.survey.channel_id),
                            "sessionId": str(getattr(self.survey, 'session_id', ''))
                        }
                        logger.info(f"Sending step webhook: {step_payload}")
                        success, response = await webhook_service.send_webhook_with_retry(
                            interaction.channel,
                            step_payload,
                            {"Authorization": f"Bearer {Config.WEBHOOK_AUTH_TOKEN}"}
                        )
                        logger.info(f"Step webhook response: success={success}, response={response}")
                        # Show n8n output to user if present
                        if response:
                            try:
                                await interaction.followup.send(str(response), ephemeral=False)
                            except Exception as e:
                                logger.warning(f"Failed to send n8n step response to user: {e}")
                    except Exception as e:
                        logger.error(f"Error sending step webhook: {e}")

                    logger.info("Calling continue_survey after step webhook")
                    await continue_survey(interaction.channel, self.survey)
                    logger.info("Returned from continue_survey after step webhook")
            except Exception as e:
                logger.error(f"Error advancing survey: {e}")
                await send_error(Strings.GENERAL_ERROR)

        except Exception as e:
            logger.error(f"Unexpected error in connects modal submission: {e}", exc_info=True)
            try:
                await send_error(Strings.GENERAL_ERROR)
                # Clean up previous message even on error to prevent stuck buttons
                await cleanup_survey_message(interaction, self.survey)
            except Exception as cleanup_error:
                logger.error(f"Error during error cleanup: {cleanup_error}")
# ==================================
# Helper Functions
# ==================================

async def cleanup_survey_message(interaction: discord.Interaction, survey: SurveyFlow):
    logger.debug(f"[{survey.user_id if survey else 'N/A'}] - cleanup_survey_message called for message ID: {survey.current_question_message_id if survey else 'N/A'}")
    """Helper function to clean up the survey question message after modal submission.
    Attempts to disable the button on the original message and then delete it.
    Handles potential errors like message not found or missing permissions gracefully.
    """
    if not survey.current_question_message_id:
        logger.debug(f"[{survey.user_id if survey else 'N/A'}] - cleanup_survey_message: No message ID to clean up.")
        return # Added missing return
    try:
        logger.debug(f"[{survey.user_id if survey else 'N/A'}] - cleanup_survey_message: Fetching message {survey.current_question_message_id}")
        original_msg = await interaction.channel.fetch_message(survey.current_question_message_id)
        logger.debug(f"[{survey.user_id if survey else 'N/A'}] - cleanup_survey_message: Message fetched successfully.")
        # Attempt to disable button (best effort)
        try:
            view = discord.ui.View.from_message(original_msg)
            if view: # Check if view exists
                changed = False
                for item in view.children:
                    if isinstance(item, discord.ui.Button):
                        item.disabled = True
                        changed = True
                if changed:
                    await original_msg.edit(view=view)
        except Exception as e_edit:
            logger.warning(f"Could not disable button on message {survey.current_question_message_id}: {e_edit}")
        # Delete the message
        await original_msg.delete()
        survey.current_question_message_id = None # Clear ID after deletion
    except discord.NotFound:
        logger.warning(f"Original survey question message {survey.current_question_message_id} not found for deletion.")
        survey.current_question_message_id = None # Clear ID if not found
    except discord.Forbidden:
         logger.error(f"Bot lacks permissions to edit/delete message {survey.current_question_message_id} in channel {interaction.channel.id}")
         # Cannot delete, but clear the ID so we don't try again
         survey.current_question_message_id = None
    except Exception as e_cleanup:
        logger.error(f"Error during survey message cleanup: {e_cleanup}")
        # Clear ID even on other errors to prevent retries
        survey.current_question_message_id = None


async def handle_modal_error(interaction: discord.Interaction):
    """Standard error handler for modal on_submit exceptions.
    Attempts to send an ephemeral error message to the user.
    """
    logger.info("DEBUG: Entered handle_modal_error for modal submission")
    try:
        if interaction.response.is_done():
            await interaction.followup.send(Strings.MODAL_SUBMIT_ERROR, ephemeral=True)
        else:
            # If defer() failed or wasn't called, try initial response
            await interaction.response.send_message(Strings.MODAL_SUBMIT_ERROR, ephemeral=True)
    except Exception as e_resp:
         logger.error(f"Failed to send error response in modal: {e_resp}")


# ==================================
# Survey Flow Logic
# ==================================

async def handle_survey_incomplete(session_id: str) -> None:
    """Handles the scenario where a survey times out before completion.
    Sends an 'incomplete' status webhook to n8n and cleans up the survey session.
    """
    survey = survey_manager.get_survey_by_session(session_id) # Use get_survey_by_session
    if not survey:
        logger.debug(f"No survey found for session_id {session_id} during incomplete handling.")
        return

    # Fetch channel using the global bot instance
    channel = None
    try:
        channel = await bot.fetch_channel(int(survey.channel_id))
    except (discord.NotFound, discord.Forbidden):
         logger.warning(f"Could not fetch channel {survey.channel_id} via bot instance.")
    except Exception as e:
         logger.error(f"Error fetching channel {survey.channel_id} via bot instance: {e}")

    if not channel:
        logger.warning(f"Channel {survey.channel_id} could not be found for incomplete survey session {session_id}")
        return

    incomplete = survey.incomplete_steps()
    # Validate IDs before webhook call
    if not survey.user_id or not survey.channel_id or not survey.session_id:
        logger.error(f"Missing required IDs for incomplete survey - user: {survey.user_id}, channel: {survey.channel_id}")
        return

    await webhook_service.send_webhook(
        channel,
        command="survey",
        status="incomplete",
        result={"incompleteSteps": incomplete}
    )

    survey_manager.remove_survey(survey.user_id) # Remove by user_id
    logger.info(f"Survey for user {survey.user_id} (session {session_id}) timed out with incomplete steps: {incomplete}")

async def handle_start_daily_survey(user_id: str, channel_id: str, session_id: str) -> None:
    """Initiates or resumes the daily survey for a user in a specific channel.
    Checks for existing sessions, verifies channel registration with n8n,
    retrieves, filters, and orders steps, then starts the survey by asking the first step.
    """
    logger.info(f"Starting daily survey for user {user_id} in channel {channel_id}")
    # Check for existing survey first
    existing_survey = survey_manager.get_survey(user_id)
    if existing_survey:
        # If survey exists, check if it's in the same channel
        if str(existing_survey.channel_id) == str(channel_id):
            logger.info(f"Resuming existing survey for user {user_id} in channel {channel_id}")
            step = existing_survey.current_step()
            if step:
                channel = await bot.fetch_channel(int(existing_survey.channel_id))
                if channel:
                    await ask_dynamic_step(channel, existing_survey, step) # Resend current step question/button
                    return
            else: # Survey exists but is somehow done? Clean up and proceed.
                logger.warning(f"Existing survey found for user {user_id} but no current step. Removing and starting new.")
                survey_manager.remove_survey(user_id)
        else:
            # Survey exists but in a different channel - this shouldn't normally happen with button start
            logger.warning(f"User {user_id} has existing survey in channel {existing_survey.channel_id}, but request is for {channel_id}. Ignoring old survey.")
            # Let the flow continue to create a new survey for the *current* channel

    # Check if channel is registered
    payload = {
        "command": "check_channel",
        "channelId": channel_id
    }
    headers = {"Authorization": f"Bearer {Config.WEBHOOK_AUTH_TOKEN}"}
    logger.info(f"First check_channel call for channel {channel_id} with payload: {payload}")
    success, data = await webhook_service.send_webhook_with_retry(None, payload, headers)
    logger.info(f"First check_channel webhook response: success={success}, raw_data={{data}}") # Log raw data

    if not success or str(data.get("output", "false")).lower() != "true":
        logger.info(f"First check_channel webhook response: success={success}, raw_data={{data}}") # Log raw data
        logger.warning(f"Channel {channel_id} not registered for surveys")
        return

    # Check channel response data
    steps = data.get("steps", [])
    logger.info(f"Extracted steps from webhook data: {{steps}}") # Log extracted steps
    channel = await bot.fetch_channel(channel_id)

    if not channel:
        logger.warning(f"Channel {channel_id} not found")
        return

    # Handle cases based on received data
    if steps:
        # Steps provided - proceed with survey
        pass
    else:
        # No steps provided - send completion message
        await channel.send(f"<@{user_id}> {Strings.SURVEY_COMPLETE_MESSAGE}")
        logger.info(f"No survey steps provided for channel {channel_id}, survey complete")
        return

    logger.info(f"Starting survey with steps: {steps}")

    # The step ordering code is not needed and has been removed.

    # --- Start New Survey Flow ---
        # --- Start New Survey Flow ---

    # Filter and order steps based on SURVEY_FLOW constant
    final_steps = [step for step in constants.SURVEY_FLOW if step in steps]

    if not final_steps:
        logger.info(f"No *required* survey steps found for channel {channel_id} after filtering {steps}.")
        channel = await bot.fetch_channel(int(channel_id))
        if channel: await channel.send(f"<@{user_id}> {Strings.SURVEY_COMPLETE_MESSAGE}")
        return

    logger.info(f"Starting new survey for user {user_id} in channel {channel_id} with steps: {final_steps}")

    # Create the survey object
    survey = survey_manager.create_survey(user_id, channel_id, final_steps, session_id) # Pass session_id

    # Ask the first step
    first_step = survey.current_step()
    if first_step:
        channel = await bot.fetch_channel(int(channel_id))
        if channel:
            logger.info(f"Fetched channel for survey: ID={channel.id}, Name={channel.name}") # Added log
            await ask_dynamic_step(channel, survey, first_step)
        else:
            logger.error(f"Could not fetch channel {channel_id} to ask first survey step.")
            survey_manager.remove_survey(user_id) # Clean up unusable survey
    else:
        # Should not happen if final_steps is not empty, but handle defensively
        logger.error(f"Survey created for user {user_id} but no first step available. Steps: {final_steps}")
        channel = await bot.fetch_channel(int(channel_id))
        if channel: await channel.send(f"<@{user_id}> {Strings.SURVEY_START_ERROR}: No steps found.")
        survey_manager.remove_survey(user_id)
async def ask_dynamic_step(channel: discord.TextChannel, survey: SurveyFlow, step_name: str) -> None: # Type hint updated
    """Asks a single step of the survey.
    Sends a message with the step question and a 'Ввести' button.
    The button's callback triggers the appropriate survey-specific modal.
    """
    # Validate inputs
    if not channel or not survey or not step_name:
        logger.error(f"Invalid ask_dynamic_step params - channel: {channel}, survey: {survey}, step: {step_name}")
        return

    user_id = survey.user_id
    logger.info(f"Asking step {step_name} for user {user_id} in channel {channel.id}")

    # Validate survey state
    if not survey.user_id or not survey.channel_id:
        logger.error(f"Invalid survey state - user_id: {survey.user_id}, channel_id: {survey.channel_id}")
        return

    try:
        # Get standardized question text for each step from Strings
        step_questions = {
            "workload_today": Strings.WORKLOAD_TODAY,
            "workload_nextweek": Strings.WORKLOAD_NEXTWEEK,
            "connects_thisweek": Strings.CONNECTS,
            "dayoff_nextweek": Strings.DAY_OFF_NEXTWEEK
        }
        question_text = step_questions.get(step_name)

        if not question_text:
             logger.error(f"No question text found for survey step: {step_name}")
             await channel.send(f"<@{user_id}> {Strings.STEP_ERROR}: Configuration error.")
             # Consider removing survey or stopping flow here
             return

        question_text = f"<@{user_id}> {question_text}" # Prepend user mention

        # Create the "Ввести" button
        button = discord.ui.Button(
            label=Strings.SURVEY_INPUT_BUTTON_LABEL, # "Ввести"
            style=discord.ButtonStyle.primary,
            custom_id=f"survey_step_{survey.session_id}_{step_name}" # Unique ID
        )

        async def button_callback(interaction: discord.Interaction):
            """Callback for the 'Ввести' button."""
            # No defer needed here, we will edit the original response directly.

            logger.info(f"Button callback triggered for step: {step_name}") # Added log

            # Defer interaction *before* doing potentially slow work (creating view)
            try:
                # Check if already responded to prevent errors
                if not interaction.response.is_done():
                    await interaction.response.defer(ephemeral=False) # Defer publicly
                    logger.info(f"Interaction deferred for step: {step_name}")
                else:
                    logger.warning(f"Interaction already responded/deferred for step: {step_name}")
            except Exception as defer_error:
                 logger.error(f"Error deferring interaction for step {step_name}: {defer_error}", exc_info=True)
                 # Attempt to notify user if possible, then return
                 try:
                     # Use followup since we might have deferred successfully before error
                     await interaction.followup.send(Strings.GENERAL_ERROR, ephemeral=True)
                 except:
                     pass
                 return

            # Verify user matches survey user
            if str(interaction.user.id) != str(survey.user_id):
                await interaction.response.send_message(Strings.SURVEY_NOT_FOR_YOU, ephemeral=True)
                return

            # Identify the correct view or modal based on step_name
            if step_name in ["workload_today", "workload_nextweek"]:
                logger.info(f"Button callback for workload survey step: {step_name}. Creating workload view.")
                # Create and send the multi-button workload view
                workload_view = create_workload_view(step_name, str(interaction.user.id), has_survey=True, continue_survey_func=continue_survey)
                logger.info(f"Workload view created: {workload_view}")
                # Need to store message references on the view for the callback to use
                # Pass the actual message object, not just the ID
                workload_view.command_msg = survey.current_message
                workload_view.buttons_msg = None # This view *is* the buttons message, will be set after sending

                # Send the workload button view
                # Instead of editing the original message, send a new message with the workload view
                logger.info(f"[{interaction.user.id}] - Attempting to send new message with workload view...")
                buttons_msg = await interaction.followup.send(
                    content=Strings.SELECT_HOURS, # Content for the new message
                    view=workload_view, # Add the new view with hour buttons
                    ephemeral=False # Make the button message visible to others
                )
                logger.info(f"[{interaction.user.id}] - New message with workload view sent. Message ID: {buttons_msg.id}")
                workload_view.buttons_msg = buttons_msg # Store the message object reference on the view

                # Disable the "Ввести" button on the original message
                try:
                    original_msg = await interaction.channel.fetch_message(survey.current_question_message_id)
                    if original_msg and original_msg.components:
                        # Assuming the "Ввести" button is the only component or the first one
                        view_to_edit = discord.ui.View.from_message(original_msg)
                        if view_to_edit and view_to_edit.children:
                            for item in view_to_edit.children:
                                if isinstance(item, discord.ui.Button):
                                    item.disabled = True
                            await original_msg.edit(view=view_to_edit)
                            logger.info(f"[{interaction.user.id}] - Disabled 'Ввести' button on message {original_msg.id}")
                        else:
                             logger.warning(f"[{interaction.user.id}] - Could not find view or children on original message {original_msg.id} to disable button.")
                    else:
                        logger.warning(f"[{interaction.user.id}] - Could not fetch original message {survey.current_question_message_id} or it has no components.")
                except discord.NotFound:
                    logger.warning(f"[{interaction.user.id}] - Original message {survey.current_question_message_id} not found when trying to disable button.")
                except Exception as e:
                    logger.error(f"[{interaction.user.id}] - Error disabling 'Ввести' button on original message {survey.current_question_message_id}: {e}", exc_info=True)


                # Removed cleanup for workload steps as per user request
                # logger.info(f"[{interaction.user.id}] - DEBUG: About to call cleanup_survey_message for original question message ID: {survey.current_question_message_id}")
                # await cleanup_survey_message(interaction, survey)
                # logger.info(f"[{interaction.user.id}] - cleanup_survey_message called for original message {survey.current_question_message_id}")

                # The WorkloadView callback should handle deleting the buttons message after a selection is made.

            elif step_name == "connects_thisweek":
                try:
                    logger.info(f"Button callback for connects_thisweek survey step: {step_name}")

                    # Verify interaction hasn't been responded to
                    if interaction.response.is_done():
                        logger.error("Interaction already responded to")
                        return

                    # Create and send modal
                    logger.info("Creating ConnectsModal instance")
                    modal_to_send = ConnectsModal(survey=survey, step_name=step_name, continue_survey_func=continue_survey) # Pass continue_survey_func
                    logger.info("Sending ConnectsModal via followup")
                    await interaction.followup.send_modal(modal_to_send)
                    logger.info("ConnectsModal sent successfully via followup")

                except discord.errors.InteractionResponded:
                    logger.error("Interaction already responded to when trying to send modal via followup")
                    return
                except Exception as e:
                    logger.error(f"Error in connects_thisweek button callback: {e}", exc_info=True)
                    try:
                        if not interaction.response.is_done():
                            await interaction.response.send_message(
                                Strings.GENERAL_ERROR,
                                ephemeral=True
                            )
                    except Exception as e:
                        logger.error(f"Error sending error response in connects_thisweek button callback: {e}")

            elif step_name == "dayoff_nextweek":
                logger.info(f"Button callback for dayoff_nextweek survey step: {step_name}. Sending button view.")
                # Create and send the day off view
                from discord_bot.views.day_off_survey import create_day_off_view # Use survey-specific view
                day_off_view = create_day_off_view(step_name, str(interaction.user.id), has_survey=True)
                # Need to store message references on the view for the callback to use
                day_off_view.command_msg = survey.current_question_message_id # Pass the ID of the initial question message
                day_off_view.buttons_msg = None # This view *is* the buttons message, will be set after sending

                # Send the day off button view
                # Since the initial interaction was deferred in ask_dynamic_step, use followup.send
                buttons_msg = await interaction.followup.send(
                    Strings.DAY_OFF_NEXTWEEK,
                    view=day_off_view,
                    ephemeral=False # Make the button message visible to others
                )
                day_off_view.buttons_msg = buttons_msg # Store the message object
                # Removed the cleanup of the original message here.
                # The DayOffView callback should handle deleting the buttons message.

            else:
                logger.error(f"Button callback triggered for unknown survey step: {step_name}")
                await interaction.response.send_message(Strings.GENERAL_ERROR, ephemeral=True)
                return

        # Assign callback and create view
        button.callback = button_callback
        view = discord.ui.View(timeout=constants.VIEW_CONFIGS[constants.ViewType.DYNAMIC]["timeout"]) # Use timeout from constants
        view.add_item(button)

        # Send the question message with the button
        logger.info(f"Attempting to send question for step {step_name} to channel ID={channel.id}, Name={channel.name} for user {user_id}") # Added log
        question_msg = await channel.send(question_text, view=view)
        survey.current_question_message_id = question_msg.id # Store message ID for cleanup
        survey.current_message = question_msg # Store the message object
        logger.info(f"Sent question for step {step_name} (msg ID: {question_msg.id}) for user {user_id}")
    except Exception as e:
        logger.error(f"Error in ask_dynamic_step for step {step_name}: {str(e)}", exc_info=True)
        try:
            await channel.send(f"<@{user_id}> {Strings.STEP_ERROR}: {str(e)}")
        except Exception as send_error:
            logger.error(f"Failed to send error message: {send_error}")

        # Only continue survey if it was a recoverable error
        if not isinstance(e, (AttributeError, ValueError)):
            try:
                survey.next_step()
                await continue_survey(channel, survey)
            except Exception as e2:
                logger.error(f"Error continuing survey after step failure: {e2}")

async def finish_survey(channel: discord.TextChannel, survey: SurveyFlow) -> None: # Type hint updated
    """Finalizes a completed survey.
    Sends the collected results in a 'complete' status webhook to n8n
    and cleans up the survey session.
    """
    logger.info(f"[{survey.user_id}] - Entering finish_survey. is_done(): {{survey.is_done()}}, Current index: {{survey.current_index}}, Total steps: {{len(survey.steps)}}") # Log state in finish_survey
    if not survey.is_done():
        return

    try:
        # Validate completion data
        if not survey or not survey.user_id or not survey.channel_id:
            raise ValueError("Invalid survey completion data")

        payload = {
            "command": "survey",
            "status": "end",
            "message": "",
            "result": {}, # Modified result to be an empty dictionary
            "userId": str(survey.user_id),
            "channelId": str(survey.channel_id),
            "sessionId": str(getattr(survey, 'session_id', ''))
        }

        logger.info(f"[{survey.user_id}] - Sending 'end' webhook for completed survey.") # Log before sending end webhook
        # Send completion webhook directly
        success, response = await webhook_service.send_webhook_with_retry(
            channel,
            payload,
            {"Authorization": f"Bearer {Config.WEBHOOK_AUTH_TOKEN}"}
        )
        logger.info(f"End webhook response: success={success}, response={response}")

        # Process n8n response
        if success and isinstance(response, dict):
            # Send main output message if present
            if output_msg := response.get("output"):
                try:
                    await channel.send(output_msg)
                except Exception as e:
                    logger.warning(f"Failed to send n8n output message to user: {e}")

            # Handle Notion ToDo fetching if URL is present
            if notion_url := response.get("url"):
                logger.info(f"[{survey.user_id}] - Notion URL found: {notion_url}. Attempting to fetch ToDos.")
                try:
                    notion_service = Notion_todos(todo_url=notion_url, days=14)
                    # Assuming get_tasks_text is made async or runs in executor
                    tasks_json_str = await notion_service.get_tasks_text()
                    tasks_data = json.loads(tasks_json_str)

                    if tasks_data.get("tasks_found"):
                        await channel.send(tasks_data.get("text", "Error: Could not format Notion tasks."))
                        logger.info(f"[{survey.user_id}] - Successfully sent Notion ToDos.")
                    else:
                        logger.info(f"[{survey.user_id}] - No Notion ToDos found or tasks_found was false.")
                        # Optionally send a message if no tasks found, or just log it.
                        # await channel.send("No relevant Notion tasks found.")

                except (ValueError, ConnectionError, json.JSONDecodeError) as notion_e:
                    logger.error(f"[{survey.user_id}] - Failed to fetch/process Notion tasks from URL {notion_url}: {notion_e}", exc_info=True)
                    try:
                        await channel.send("Дякую. \nЧудового дня!") # Send fallback message on Notion error
                    except Exception as send_e:
                         logger.error(f"Failed to send fallback message after Notion error: {send_e}")
                except Exception as e: # Catch any other unexpected errors during Notion processing
                    logger.error(f"[{survey.user_id}] - Unexpected error during Notion task fetching for URL {notion_url}: {e}", exc_info=True)
                    try:
                        await channel.send("Дякую. \nЧудового дня!") # Send fallback message
                    except Exception as send_e:
                         logger.error(f"Failed to send fallback message after unexpected Notion error: {send_e}")
            else:
                logger.info(f"[{survey.user_id}] - No Notion URL provided in n8n response.")

        elif not success:
            # Handle webhook failure
             logger.error(f"[{survey.user_id}] - Completion webhook failed. Response: {response}")
             # Keep existing error message logic below

        logger.info(f"Survey completed processing for user {survey.user_id} with results: {survey.results}")

    except Exception as e:
        # This catches errors *before* or *during* the webhook call, or if success is False and we re-raise
        logger.error(f"Error completing survey for user {survey.user_id}: {str(e)}", exc_info=True) # Added user_id and exc_info
        try:
            await channel.send(
                f"<@{survey.user_id}> Помилка при завершенні: {str(e)}"
            )
        except Exception as send_error:
            logger.error(f"Failed to send completion error: {send_error}")
    finally:
        survey_manager.remove_survey(survey.user_id) # Remove by user_id