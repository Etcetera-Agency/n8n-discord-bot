import asyncio
import discord
from typing import Optional, List, Any # Added Any
from config import ViewType, logger, Strings, Config, constants # Added constants
from services import survey_manager, webhook_service
from services.survey import SurveyFlow # Added import
# Removed factory import
from bot.views.workload import create_workload_view # Added import

# ==================================
# Survey-Specific Modals
# ==================================

class ConnectsModal(discord.ui.Modal):
    """Modal specifically for handling the 'connects' step in the survey."""
    def __init__(self, survey: SurveyFlow, step_name: str):
        """Initializes the ConnectsModal."""
        self.survey = survey
        self.step_name = step_name
        super().__init__(title=Strings.CONNECTS_MODAL, timeout=300)

        self.connects_input = discord.ui.TextInput(
            label=Strings.CONNECTS_INPUT_LABEL,
            placeholder=Strings.CONNECTS_INPUT_PLACEHOLDER,
            min_length=1,
            max_length=3
        )
        self.add_item(self.connects_input)

    async def on_submit(self, interaction: discord.Interaction):
        """Handles the modal submission for the connects step."""
        user_input = self.connects_input.value
        error_msg = Strings.CONNECTS_INPUT_ERROR
        is_valid = user_input.isdigit()

        try:
            if not is_valid:
                await interaction.response.send_message(error_msg, ephemeral=True)
                return

            await interaction.response.defer(ephemeral=True, thinking=False)

            if str(interaction.user.id) != str(self.survey.user_id) or \
               str(interaction.channel.id) != str(self.survey.channel_id):
                await interaction.followup.send(Strings.GENERAL_ERROR, ephemeral=True)
                return

            self.survey.add_result(self.step_name, user_input) # Store as string
            await cleanup_survey_message(interaction, self.survey)
            await interaction.followup.send(Strings.INPUT_SAVED, ephemeral=True)
            self.survey.next_step()

            if self.survey.is_done():
                await finish_survey(interaction.channel, self.survey)
            else:
                await continue_survey(interaction.channel, self.survey)

        except Exception as e:
            logger.error(f"Error in ConnectsModal on_submit: {e}", exc_info=True)
            await handle_modal_error(interaction)


class DayOffModal(discord.ui.Modal):
    """Modal specifically for handling the 'dayoff_nextweek' step in the survey."""
    def __init__(self, survey: SurveyFlow, step_name: str):
        """Initializes the DayOffModal."""
        self.survey = survey
        self.step_name = step_name # Should be "dayoff_nextweek"
        super().__init__(title=Strings.DAY_OFF_NEXTWEEK_MODAL, timeout=300)

        self.days_input = discord.ui.TextInput(
            label=Strings.DAY_OFF_INPUT_LABEL,
            placeholder=Strings.DAY_OFF_INPUT_PLACEHOLDER,
            style=discord.TextStyle.short, # Use short for single line
            required=False # Allow empty input for "no days off"
        )
        self.add_item(self.days_input)

    async def on_submit(self, interaction: discord.Interaction):
        """Handles the modal submission for the dayoff_nextweek step."""
        # Input can be empty or comma-separated days
        user_input = self.days_input.value.strip()
        # Basic validation: just store the string for now. n8n can parse.
        # If required=False, empty string is valid.

        try:
            await interaction.response.defer(ephemeral=True, thinking=False)

            if str(interaction.user.id) != str(self.survey.user_id) or \
               str(interaction.channel.id) != str(self.survey.channel_id):
                await interaction.followup.send(Strings.GENERAL_ERROR, ephemeral=True)
                return

            # Store raw input string (could be empty)
            self.survey.add_result(self.step_name, user_input if user_input else "Nothing") # Send "Nothing" if empty

            await cleanup_survey_message(interaction, self.survey)
            await interaction.followup.send(Strings.INPUT_SAVED, ephemeral=True)
            self.survey.next_step()

            if self.survey.is_done():
                await finish_survey(interaction.channel, self.survey)
            else:
                await continue_survey(interaction.channel, self.survey)

        except Exception as e:
            logger.error(f"Error in DayOffModal on_submit: {e}", exc_info=True)
            await handle_modal_error(interaction)

# ==================================
# Helper Functions
# ==================================

async def cleanup_survey_message(interaction: discord.Interaction, survey: SurveyFlow):
    """Helper function to clean up the survey question message after modal submission.
    Attempts to disable the button on the original message and then delete it.
    Handles potential errors like message not found or missing permissions gracefully.
    """
    if not survey.current_question_message_id:
        return # Added missing return
    try:
        original_msg = await interaction.channel.fetch_message(survey.current_question_message_id)
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

    # Fetch channel using bot instance if available, otherwise fall back
    bot_instance = getattr(survey, 'bot', None) # Check if bot instance is stored
    channel = None
    if bot_instance:
        try:
            channel = await bot_instance.fetch_channel(int(survey.channel_id))
        except (discord.NotFound, discord.Forbidden):
             logger.warning(f"Could not fetch channel {survey.channel_id} via bot instance.")
        except Exception as e:
             logger.error(f"Error fetching channel {survey.channel_id} via bot instance: {e}")

    if not channel: # Fallback if bot instance not available or fetch failed
        try:
            # This might not work reliably depending on cache state
            channel = discord.utils.get(discord.utils.get_all_channels(), id=int(survey.channel_id))
        except Exception as e:
             logger.error(f"Error getting channel {survey.channel_id} via utils: {e}")

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

async def handle_start_daily_survey(bot_instance: discord.Client, user_id: str, channel_id: str, session_id: str) -> None:
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
                channel = await bot_instance.fetch_channel(int(existing_survey.channel_id))
                if channel:
                    # Store bot instance for potential use in timeout handler
                    existing_survey.bot = bot_instance
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
    success, data = await webhook_service.send_webhook_with_retry(None, payload, headers)
    
    if not success or str(data.get("output", "false")).lower() != "true":
        logger.warning(f"Channel {channel_id} not registered for surveys")
        return
    
    # Check channel response data
    steps = data.get("steps", [])
    channel = await bot_instance.fetch_channel(channel_id)
    
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

    # Define the desired order of steps
    step_order = ["workload_today", "workload_nextweek", "connects", "dayoff_nextweek"]
    ordered_steps = []
    other_steps = []

    # Separate and order the steps
    for step in step_order:
        if step in steps:
            ordered_steps.append(step)
            steps.remove(step)  # remove from original list to avoid duplicates

    other_steps = [step for step in steps]  # remaining steps are "other" steps
    final_steps = ordered_steps + other_steps  # combine ordered steps with other steps
    steps = final_steps  # reassign steps with ordered steps

    logger.info(f"Ordered survey steps: {steps}")

    # --- Start New Survey Flow ---
    try:
        # Check if channel is registered via webhook
        payload = { "command": "check_channel", "channelId": channel_id }
        headers = {"Authorization": f"Bearer {Config.WEBHOOK_AUTH_TOKEN}"}
        success, data = await webhook_service.send_webhook_with_retry(None, payload, headers)

        if not success or str(data.get("output", "false")).lower() != "true":
            logger.warning(f"Channel {channel_id} not registered for surveys via webhook check.")
            # Optionally send a message to the user/channel?
            return

        # Get steps from n8n response
        n8n_steps = data.get("steps", [])
        if not n8n_steps:
            logger.info(f"No survey steps provided by n8n for channel {channel_id}. Sending complete message.")
            channel = await bot_instance.fetch_channel(int(channel_id))
            if channel: await channel.send(f"<@{user_id}> {Strings.SURVEY_COMPLETE_MESSAGE}")
            return

        # Filter and order steps based on REQUIRED_SURVEY_STEPS constant
        final_steps = [step for step in constants.REQUIRED_SURVEY_STEPS if step in n8n_steps]

        if not final_steps:
            logger.info(f"No *required* survey steps found for channel {channel_id} after filtering {n8n_steps}.")
            channel = await bot_instance.fetch_channel(int(channel_id))
            if channel: await channel.send(f"<@{user_id}> {Strings.SURVEY_COMPLETE_MESSAGE}")
            return

        logger.info(f"Starting new survey for user {user_id} in channel {channel_id} with steps: {final_steps}")

        # Create the survey object
        survey = survey_manager.create_survey(user_id, channel_id, final_steps, session_id) # Pass session_id
        survey.bot = bot_instance # Store bot instance

        # Ask the first step
        first_step = survey.current_step()
        if first_step:
            channel = await bot_instance.fetch_channel(int(channel_id))
            if channel:
                await ask_dynamic_step(channel, survey, first_step)
            else:
                logger.error(f"Could not fetch channel {channel_id} to ask first survey step.")
                survey_manager.remove_survey(user_id) # Clean up unusable survey
        else:
            # Should not happen if final_steps is not empty, but handle defensively
            logger.error(f"Survey created for user {user_id} but no first step available. Steps: {final_steps}")
            channel = await bot_instance.fetch_channel(int(channel_id))
            if channel: await channel.send(f"<@{user_id}> {Strings.SURVEY_START_ERROR}: No steps found.")
            survey_manager.remove_survey(user_id)

    except Exception as e:
        logger.error(f"Error in handle_start_daily_survey: {e}")
        # Try to send an error message to the channel
        survey = None
        try:
            channel = await bot_instance.fetch_channel(int(channel_id))
            await channel.send(f"<@{user_id}> {Strings.SURVEY_START_ERROR}: {str(e)}")
        except:
            logger.error(f"Could not send error message to channel {channel_id}")

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
            "connects": Strings.CONNECTS,
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
            # Verify user matches survey user
            if str(interaction.user.id) != str(survey.user_id):
                await interaction.response.send_message(Strings.SURVEY_NOT_FOR_YOU, ephemeral=True)
                return

            # Identify the correct view or modal based on step_name
            if step_name in ["workload_today", "workload_nextweek"]:
                logger.info(f"Button callback for workload survey step: {step_name}. Sending button view.")
                # Create and send the multi-button workload view
                workload_view = create_workload_view(step_name, str(interaction.user.id), has_survey=True)
                # Need to store message references on the view for the callback to use
                workload_view.command_msg = survey.current_question_message_id # Pass the ID of the initial question message
                workload_view.buttons_msg = None # This view *is* the buttons message, will be set after sending

                # Send the workload button view
                # Since the initial interaction was deferred in ask_dynamic_step, use followup.send
                buttons_msg = await interaction.followup.send(
                    "Оберіть кількість годин:", # Or appropriate string
                    view=workload_view,
                    ephemeral=False # Make the button message visible to others
                )
                workload_view.buttons_msg = buttons_msg # Store the message object

                # Clean up the original single button message
                if survey.current_question_message_id:
                    try:
                        original_msg = await interaction.channel.fetch_message(survey.current_question_message_id)
                        await original_msg.delete()
                        survey.current_question_message_id = None # Clear ID after deletion
                    except discord.NotFound:
                        logger.warning(f"Original survey question message {survey.current_question_message_id} not found for deletion after sending workload view.")
                        survey.current_question_message_id = None
                    except discord.Forbidden:
                        logger.error(f"Bot lacks permissions to delete original survey question message {survey.current_question_message_id}")
                        survey.current_question_message_id = None
                    except Exception as e_cleanup:
                        logger.error(f"Error deleting original survey question message: {e_cleanup}")
                        survey.current_question_message_id = None

            elif step_name == "connects":
                logger.info(f"Button callback for connects survey step: {step_name}. Sending modal.")
                modal_to_send = ConnectsModal(survey=survey, step_name=step_name)
                await interaction.response.send_modal(modal_to_send)

            elif step_name == "dayoff_nextweek":
                logger.info(f"Button callback for dayoff_nextweek survey step: {step_name}. Sending modal.")
                modal_to_send = DayOffModal(survey=survey, step_name=step_name)
                await interaction.response.send_modal(modal_to_send)

            else:
                logger.error(f"Button callback triggered for unknown survey step: {step_name}")
                await interaction.response.send_message(Strings.GENERAL_ERROR, ephemeral=True)
                return

        # Assign callback and create view
        button.callback = button_callback
        view = discord.ui.View(timeout=constants.SURVEY_STEP_TIMEOUT) # Use timeout from constants
        view.add_item(button)

        # Send the question message with the button
        question_msg = await channel.send(question_text, view=view)
        survey.current_question_message_id = question_msg.id # Store message ID for cleanup
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

async def continue_survey(channel: discord.TextChannel, survey: SurveyFlow) -> None: # Type hint updated
    """Advances the survey to the next step or finishes it if all steps are done.
    Called after a modal for a step is successfully submitted.
    """
    try:
        # Keep previous messages intact, only proceed to next step
        next_step = survey.current_step()
        if next_step:
            await ask_dynamic_step(channel, survey, next_step)
        else:
            await finish_survey(channel, survey)
            
    except Exception as e:
        logger.error(f"Error continuing survey: {e}")
        try:
            await channel.send(f"<@{survey.user_id}> Помилка при переході між кроками: {str(e)}")
        except Exception as e2:
            logger.error(f"Error sending error message to channel: {e2}")


async def finish_survey(channel: discord.TextChannel, survey: SurveyFlow) -> None: # Type hint updated
    """Finalizes a completed survey.
    Sends the collected results in a 'complete' status webhook to n8n
    and cleans up the survey session.
    """
    if not survey.is_done():
        return
        
    try:
        # Validate completion data
        if not survey or not survey.user_id or not survey.channel_id:
            raise ValueError("Invalid survey completion data")
            
        payload = {
            "command": "survey",
            "status": "complete",
            # Ensure result structure matches requirements exactly
            "result": {
                "workload_today": survey.results.get("workload_today", ""),
                "workload_nextweek": survey.results.get("workload_nextweek", ""),
                "connects": survey.results.get("connects", ""),
                # Ensure dayoff is handled correctly (list or "Nothing")
                "dayoff_nextweek": survey.results.get("dayoff_nextweek", "")
            },
            "userId": str(survey.user_id),
            "channelId": str(survey.channel_id),
            "sessionId": str(getattr(survey, 'session_id', ''))
        }
        
        # Send completion webhook directly
        success, response = await webhook_service.send_webhook_with_retry(
            channel,
            payload,
            {"Authorization": f"Bearer {Config.WEBHOOK_AUTH_TOKEN}"}
        )

        if not success:
            raise Exception(f"Completion webhook failed: {response}")
            
        logger.info(f"Survey completed for user {survey.user_id} with results: {survey.results}")
        
    except Exception as e:
        logger.error(f"Error completing survey: {str(e)}")
        try:
            await channel.send(
                f"<@{survey.user_id}> Помилка при завершенні: {str(e)}"
            )
        except Exception as send_error:
            logger.error(f"Failed to send completion error: {send_error}")
    finally:
        survey_manager.remove_survey(survey.user_id) # Remove by user_id