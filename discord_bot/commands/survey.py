import asyncio
import discord # type: ignore
from discord.ext import commands # type: ignore # Import commands for bot type hinting
import json # Added for Notion ToDo JSON parsing
from typing import Optional, List, Any # Added Any
from config import ViewType, logger, Strings, Config, constants # Added constants
from services import survey_manager, webhook_service
from services.notion_todos import Notion_todos # Added for Notion ToDo fetching
from services.survey import SurveyFlow # Added import
# Removed factory import
from discord_bot.views.workload_survey import create_workload_view # Use survey-specific view
# Removed: from bot import bot # Import the bot instance from the root bot.py
from discord_bot.views.model_connects_survey import ConnectsModal # Import the moved modal
from discord_bot.views.day_off_survey import create_day_off_view # Use survey-specific view

# ==================================
# Helper Functions
# ==================================


async def cleanup_survey_message(interaction: discord.Interaction, survey: SurveyFlow): # Removed survey_id from log
    # logger.debug(f"[{survey.user_id if survey else 'N/A'}] - cleanup_survey_message called with message ID: {survey.current_question_message_id if survey else 'N/A'}")
    """Helper function to clean up the survey question message after modal submission.
    Attempts to disable the button on the original message and then delete it.
    Handles potential errors like message not found or missing permissions gracefully.
    """
    if not survey.current_question_message_id:
        # logger.debug(f"[{survey.user_id if survey else 'N/A'}] - cleanup_survey_message: No message ID to clean up.")
        return # Added missing return
    try:
        # logger.debug(f"[{survey.user_id if survey else 'N/A'}] - cleanup_survey_message: Fetching message {survey.current_question_message_id}")
        original_msg = await interaction.channel.fetch_message(survey.current_question_message_id)
        # logger.debug(f"[{survey.user_id if survey else 'N/A'}] - cleanup_survey_message: Message fetched successfully.")
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

async def handle_survey_incomplete(bot: commands.Bot, session_id: str) -> None: # Added bot parameter
    """Handles the scenario where a survey times out or is otherwise incomplete.
    Sends an 'incomplete' status webhook to n8n and cleans up the survey session.
    """
    survey = survey_manager.get_survey_by_session(session_id) # Use get_survey_by_session
    if not survey:
        # logger.debug(f"No survey found for session_id {session_id} during incomplete handling.")
        return

    # Fetch channel using the provided bot instance
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
        logger.error(f"Missing required IDs for incomplete survey - user: {survey.session_id}, channel: {survey.channel_id}")
        return

    # Notify user about timeout
    try:
        logger.info(f"Sending timeout message to user {survey.user_id} in channel {survey.channel_id}")
        await channel.send(f"<@{survey.user_id}> {Strings.TIMEOUT_MESSAGE}")
        logger.info(f"Successfully sent timeout message to user {survey.user_id}")
    except Exception as e:
        logger.error(f"Failed to send timeout message to user {survey.user_id}: {e}")

    survey_manager.remove_survey(survey.channel_id) # Remove by channel_id
    logger.info(f"Survey for user {survey.session_id} (session {session_id}) timed out with incomplete steps: {incomplete}")

async def handle_start_daily_survey(bot: commands.Bot, user_id: str, channel_id: str, session_id: str) -> None: # Added bot parameter
    """Initiates or resumes the daily survey for a channel.
    Checks for existing sessions, verifies channel registration with n8n,
    retrieves, filters, and orders steps, then starts the survey by asking the first step.
    """
    logger.info(f"Starting daily survey for channel {channel_id} (user: {user_id})")
    # Check for existing survey first
    existing_survey = survey_manager.get_survey(channel_id) # Get by channel_id
    if existing_survey:
        # If survey exists, check if it's in the same channel
        if str(existing_survey.channel_id) == str(channel_id) and str(existing_survey.user_id) == str(user_id): # Also check user_id for session uniqueness
            logger.info(f"Resuming existing survey for user {user_id} in channel {channel_id}")
            step = existing_survey.current_step()
            if existing_survey.active_view:
                existing_survey.active_view.stop()
            if step:
                channel = await bot.fetch_channel(int(existing_survey.channel_id))
                if channel:
                    await ask_dynamic_step(bot, channel, existing_survey, step) # Pass bot instance
                    return
            else: # Survey exists but is somehow done? Clean up and proceed.
                logger.warning(f"Existing survey found for channel {channel_id} but no current step. Removing and starting new.")
                survey_manager.remove_survey(channel_id) # Remove by channel_id
        else: # Corrected indentation and removed extra 'else'
            # Survey exists but in a different channel - this shouldn't normally happen with button start
            logger.warning(f"User {user_id} has existing survey in channel {existing_survey.channel_id}, but request is for {channel_id}. Ignoring old survey.")
            # Let the flow continue to create a new survey for the *current* channel


    # Check if channel is registered
    payload = { # Payload for check_channel webhook
        "command": "check_channel",
        "channelId": channel_id,
        "sessionId": session_id # Added session_id
    }
    headers = {"Authorization": f"Bearer {Config.WEBHOOK_AUTH_TOKEN}"}
    headers = {"Authorization": f"Bearer {Config.WEBHOOK_AUTH_TOKEN}"}
    logger.info(f"First check_channel call for channel {channel_id} with payload: {payload}")
    success, data = await webhook_service.send_webhook_with_retry(None, payload, headers)
    # logger.debug(f"First check_channel webhook response: success={success}, raw_data={data}") # Log raw data at debug level
    if not success or not data or str(data.get("output", "false")).lower() != "true":
        logger.info(f"First check_channel webhook response: success={success}, raw_data={data}") # Log raw data
        logger.warning(f"Channel {channel_id} not registered for surveys")
        return

    # Check channel response data
    steps = data.get("steps", []) if data else []
    # logger.debug(f"Extracted steps from webhook data: {steps}") # Log extracted steps at debug level
    channel = await bot.fetch_channel(channel_id)
    if not channel:
        logger.warning(f"Channel {channel_id} not found")
        return

    # Handle cases based on received data
    if steps:
        # Steps provided - proceed with survey
        pass
    else:
        # No steps provided - finish the survey flow
        logger.info(f"No survey steps provided for channel {channel_id}, finishing survey.")
        # Create a minimal survey object to pass to finish_survey
        # Use create_survey so it's added to the manager and can be retrieved by finish_survey
        try:
            minimal_survey = survey_manager.create_survey(user_id, channel_id, [], session_id)
            # Mark the minimal survey as done immediately
            minimal_survey.current_index = len(minimal_survey.steps) # Set index to indicate completion
            await finish_survey(bot, channel, minimal_survey)
        except ValueError as e:
            logger.error(f"Failed to create minimal survey for channel {channel_id}: {e}")
            # Optionally send an error message to the channel here if creation fails
            if channel:
                 await channel.send(f"<@{user_id}> {Strings.SURVEY_START_ERROR}: Failed to initialize survey.")
        return

    logger.info(f"Starting survey with steps: {steps}")

    # The step ordering code is not needed and has been removed.

    # --- Start New Survey Flow ---

    # Filter and order steps based on SURVEY_FLOW constant
    final_steps = [step for step in constants.SURVEY_FLOW if step in steps]

    if not final_steps:
        logger.info(f"No *required* survey steps found for channel {channel_id} after filtering {steps}.")
        channel = await bot.fetch_channel(int(channel_id))
        if channel: await channel.send(f"{Strings.SURVEY_COMPLETE_MESSAGE}")
        return

    logger.info(f"Starting new survey for user {user_id} in channel {channel_id} with steps: {final_steps}")

    # Create the survey object
    survey = survey_manager.create_survey(user_id, channel_id, final_steps, session_id) # Create survey with all required IDs

    # Ask the first step
    first_step = survey.current_step()
    if first_step:
        channel = await bot.fetch_channel(int(channel_id))
        if channel:
            logger.info(f"Fetched channel for survey: ID={channel.id}, Name={channel.name} (user: {user_id})") # Added log
            await ask_dynamic_step(bot, channel, survey, first_step) # Pass bot instance
        else:
            logger.error(f"Could not fetch channel {channel_id} to ask first survey step.")
            survey_manager.remove_survey(channel_id) # Clean up unusable survey by channel_id
    else:
        # Should not happen if final_steps is not empty, but handle defensively
        logger.error(f"Survey created for channel {channel_id} but no first step available. Steps: {final_steps}")
        channel = await bot.fetch_channel(int(channel_id))
        if channel: await channel.send(f"<@{user_id}> {Strings.SURVEY_START_ERROR}: No steps found.")
        survey_manager.remove_survey(channel_id) # Clean up by channel_id

async def ask_dynamic_step(bot: commands.Bot, channel: discord.TextChannel, survey: SurveyFlow, step_name: str) -> None: # Added bot parameter, Type hint updated
    """Asks a single step of the survey.
    Sends a message with the step question and a 'Ввести' button.
    The button's callback triggers the appropriate survey-specific modal.
    """
    # Validate inputs
    if not channel or not survey or not step_name:
        logger.error(f"Invalid ask_dynamic_step params - channel: {channel}, survey: {survey}, step: {step_name}")
        return # Exit if parameters are invalid

    user_id = survey.user_id
    logger.info(f"Asking step {step_name} for user {user_id} in channel {channel.id}")

    # Validate survey state
    if not survey.user_id or not survey.channel_id:
        logger.error(f"Invalid survey state - user_id: {survey.session_id}, channel_id: {survey.channel_id}")
        return

    try:
        # Get standardized question text for each step from Strings
        step_questions = {
            "workload_today": Strings.WORKLOAD_TODAY,
            "workload_nextweek": Strings.WORKLOAD_NEXTWEEK,
            "connects_thisweek": Strings.CONNECTS,
            "day_off_nextweek": Strings.DAY_OFF_NEXTWEEK
        }
        question_text = step_questions.get(step_name)

        if not question_text:
             logger.error(f"No question text found for survey step: {step_name}")
             await channel.send(f"<@{user_id}> {Strings.STEP_ERROR}: Configuration error.")
             # Consider removing survey or stopping flow here
             return

        question_text = f"<@{user_id}> {question_text}" # Prepend user mention

        # Create the "Ввести" button
        button = discord.ui.Button( # Create the button for the step
            label=Strings.SURVEY_INPUT_BUTTON_LABEL, # "Ввести"
            style=discord.ButtonStyle.primary,
            custom_id=f"survey_step_{survey.session_id}_{step_name}" # Unique ID
        )

        async def button_callback(interaction: discord.Interaction):
            """Callback for the 'Ввести' button."""
            original_msg = None # Initialize original_msg to None
            logger.info(f"[{interaction.user.id}] - Button callback triggered for step: {step_name} in channel {interaction.channel.id}") # Added log with user ID

            # No defer needed here, we will edit the original response directly.


            logger.info(f"Button callback triggered for step: {step_name} in channel {interaction.channel.id} by user {interaction.user.id}") # Added log with user ID

            # Verify user matches survey user
            # Retrieve the survey using channel_id
            current_survey = survey_manager.get_survey(str(interaction.channel.id))
            if not current_survey or str(interaction.user.id) != str(current_survey.user_id):
                logger.warning(f"User {interaction.user.id} attempted to interact with survey in channel {interaction.channel.id} but it belongs to user {current_survey.user_id if current_survey else 'N/A'}")
                # Use send_message as this is the initial response
                await interaction.response.send_message(Strings.SURVEY_NOT_FOR_YOU, ephemeral=False)
                return # Exit if user/channel mismatch

            # Disable the button on the original message
            try:
                original_msg = await interaction.channel.fetch_message(current_survey.current_question_message_id)
                if original_msg:
                    view = discord.ui.View.from_message(original_msg)
                    if view:
                        changed = False # Initialize changed flag
                        for item in view.children:
                            if isinstance(item, discord.ui.Button) and item.custom_id == f"survey_step_{current_survey.session_id}_{step_name}":
                                item.disabled = True
                                changed = True # Set changed flag
                                break # Found and disabled the button, no need to continue loop
                        if changed: # Only edit if a button was disabled
                            await original_msg.edit(view=view)
                            logger.debug(f"Disabled button on message {original_msg.id} for step {step_name}")

            except Exception as disable_error:
                logger.warning(f"Could not disable button on message {current_survey.current_question_message_id} for step {step_name}: {disable_error}")

            # Add "⏳" reaction to the original message
            try:
                # original_msg is fetched above, reuse it if available
                if original_msg and not any(r.emoji == "⏳" for r in original_msg.reactions): # Avoid adding reaction if already present
                    await original_msg.add_reaction(Strings.PROCESSING) # Add reaction to the original message
                    # logger.debug(f"Added {Strings.PROCESSING} reaction to message {original_msg.id} in channel {interaction.channel.id}")
            except Exception as reaction_error:
                logger.warning(f"Could not add {Strings.PROCESSING} reaction to message {current_survey.current_question_message_id} in channel {interaction.channel.id}: {reaction_error}")

            # Identify the correct view or modal based on step_name
            if step_name in ["workload_today", "workload_nextweek"]:
                # Defer interaction for workload view as it's a followup message
                try:
                    if not interaction.response.is_done():
                        await interaction.response.defer(ephemeral=False) # Defer publicly
                except Exception as defer_error:
                    logger.error(f"Error deferring interaction for workload step {step_name}: {defer_error}", exc_info=True)
                    try:
                        await interaction.response.send_message(Strings.GENERAL_ERROR, ephemeral=False)
                    except:
                        pass
                    return

                logger.info(f"Button callback for workload survey step: {step_name}. Creating workload view.")
                # Create the multi-button workload view
                # Pass the current_survey object and continue_survey function to the view factory
                workload_view = create_workload_view(bot, step_name, str(interaction.user.id), has_survey=True, continue_survey_func=lambda c, s: continue_survey(bot, c, s), survey=current_survey, command_msg=original_msg) # Pass bot instance to continue_survey and the original message, added bot instance
                # logger.debug(f"[{current_survey.session_id.split('_')[0]}] - Workload view created: {workload_view}") # Keep debug

                # Send the workload view as a new message instead of editing the original
                # logger.debug(f"[{current_survey.session_id.split('_')[0]}] - Attempting to send workload view via followup.send") # Added log
                try:
                    buttons_msg = await interaction.followup.send(
                        content=Strings.SELECT_HOURS,
                        view=workload_view,
                        ephemeral=False
                    )
                    logger.info(f"[Channel {current_survey.session_id.split('_')[0]}] - Sent workload view as new message {buttons_msg.id}.") # Modified log
                    # Store the message object reference on the view for the callback to use
                    workload_view.buttons_msg = buttons_msg # Store the new message object

                    # Remove the processing reaction from the original command message
                    if original_msg:
                        try:
                            await original_msg.remove_reaction(Strings.PROCESSING, interaction.client.user)
                            logger.debug(f"Removed {Strings.PROCESSING} reaction from original command message {original_msg.id}")
                        except Exception as remove_reaction_error:
                            logger.warning(f"Could not remove {Strings.PROCESSING} reaction from original command message {original_msg.id}: {remove_reaction_error}")
                except Exception as e:
                    logger.error(f"[Channel {current_survey.session_id.split('_')[0]}] - Error sending workload view as new message: {e}", exc_info=True) # Modified log
                    # Attempt to send error message via followup if sending failed
                    try:
                        # logger.debug(f"[{current_survey.session_id.split('_')[0]}] - Attempting to send error message via followup.send after failure") # Added log
                        await interaction.followup.send(Strings.GENERAL_ERROR, ephemeral=False)
                        # logger.debug(f"[{current_survey.session_id.split('_')[0]}] - Sent error message via followup.send") # Added log
                    except Exception as e_send_error: # Added specific exception for error sending
                        logger.error(f"[Channel {current_survey.session_id.split('_')[0]}] - Failed to send error message after workload view send failure: {e_send_error}", exc_info=True) # Added log

            elif step_name == "connects_thisweek":
                try:
                    logger.info(f"Button callback for connects_thisweek survey step: {step_name}")

                    # Create and send modal as the initial response
                    # Pass the current_survey object and dependencies
                    modal_to_send = ConnectsModal(
                        survey=current_survey,
                        step_name=step_name,
                        finish_survey_func=lambda c, s: finish_survey(bot, c, s), # Pass bot instance to finish_survey
                        webhook_service_instance=webhook_service, # Pass webhook_service instance
                        bot_instance=bot # Pass bot instance
                    )
                    # Send modal as the initial response
                    await interaction.response.send_modal(modal_to_send)

                except discord.errors.InteractionResponded:
                    logger.error("Interaction already responded to when trying to send modal")
                    return
                except Exception as e:
                    logger.error(f"Error in connects_thisweek button callback: {e}", exc_info=True)
                    try:
                        # Use send_message as this is the initial response
                        if not interaction.response.is_done():
                            await interaction.response.send_message(
                                Strings.GENERAL_ERROR,
                                ephemeral=False
                            )
                        else:
                             await interaction.followup.send(Strings.GENERAL_ERROR, ephemeral=False) # Added followup for already responded
                    except Exception as e:
                        logger.error(f"Error sending error response in connects_thisweek button callback: {e}")

            elif step_name == "day_off_nextweek":
                # Defer interaction for day off view as it's a followup message
                await interaction.response.defer()
                logger.info(f"Button callback for day_off_nextweek survey step: {step_name}. Creating day off view.")
                from discord_bot.views.day_off_survey import create_day_off_view # Use survey-specific view
                logger.debug(f"[{interaction.user.id}] - Calling create_day_off_view for step: {step_name}")
                try:
                    # Pass the current_survey object and continue_survey function to the view factory
                    day_off_view = create_day_off_view(bot, step_name, str(interaction.user.id), has_survey=True, continue_survey_func=lambda c, s: continue_survey(bot, c, s), survey=current_survey, command_msg=original_msg) # Pass bot instance and original_msg to create_day_off_view
                    logger.debug(f"[{interaction.user.id}] - create_day_off_view returned: {day_off_view}")

                    # Send the day off view as a new message instead of editing the original
                    logger.debug(f"[{interaction.user.id}] - Attempting to send day off view via followup.send")
                    try:
                        buttons_msg = await interaction.followup.send(
                            Strings.DAY_OFF_NEXTWEEK,
                            view=day_off_view,
                            ephemeral=False
                        )
                        logger.debug(f"[{interaction.user.id}] - interaction.followup.send returned message ID: {buttons_msg.id}")
                        logger.info(f"[Channel {current_survey.session_id.split('_')[0]}] - Sent day off view as new message {buttons_msg.id}.")
                        # Store the message object reference on the view for the callback to use
                        day_off_view.buttons_msg = buttons_msg # Store the new message object

                    except discord.errors.NotFound:
                        logger.error(f"[Channel {current_survey.session_id.split('_')[0]}] - Webhook not found when sending day off view. Interaction might be stale.", exc_info=True)
                        # Inform the user that the interaction might be stale
                        try:
                            await interaction.followup.send("It seems there was an issue with the interaction. Please try starting the survey again.", ephemeral=True)
                        except Exception as e_send_error:
                            logger.error(f"[Channel {current_survey.session_id.split('_')[0]}] - Failed to send stale interaction message: {e_send_error}", exc_info=True)
                    except Exception as e:
                        logger.error(f"[Channel {current_survey.session_id.split('_')[0]}] - Error sending day off view as new message: {e}", exc_info=True)
                        # Attempt to send a generic error message via followup if sending failed
                        try:
                            await interaction.followup.send(Strings.GENERAL_ERROR, ephemeral=False)
                        except Exception as e_send_error:
                            logger.error(f"[Channel {current_survey.session_id.split('_')[0]}] - Failed to send generic error message after day off view send failure: {e_send_error}", exc_info=True)

                except Exception as e:
                    logger.error(f"[{interaction.user.id}] - Error creating day off view for step {step_name}: {e}", exc_info=True)
                    # Attempt to send a generic error message to the user
                    try:
                        await interaction.followup.send(Strings.GENERAL_ERROR, ephemeral=False)
                    except Exception as e_send_error:
                        logger.error(f"[{interaction.user.id}] - Failed to send error message after view creation failure: {e_send_error}", exc_info=True)


            else:
                logger.error(f"Button callback triggered for unknown survey step: {step_name}")
                # Use send_message as this is the initial response
                await interaction.response.send_message(Strings.GENERAL_ERROR, ephemeral=False)
                return

        # Assign callback and create view
        button.callback = button_callback
        button.callback = button_callback
        view = discord.ui.View(timeout=constants.VIEW_CONFIGS[constants.ViewType.DYNAMIC]["timeout"]) # Use timeout from constants
        
        # Add timeout handler to clean up and notify user
        async def on_timeout():
            logger.info(f"Survey step {step_name} timed out for user {user_id}")
            # Get the latest survey state from the manager
            current_survey = survey_manager.get_survey(survey.channel_id)
            if current_survey:
                await handle_survey_incomplete(bot, current_survey.session_id)
            else:
                logger.error(f"Survey not found for channel {survey.channel_id} during timeout")
            
        view.on_timeout = on_timeout
        
        view.add_item(button)
        survey.active_view = view  # Attach view to survey

        # Send the question message with the button
        logger.info(f"Attempting to send question for step {step_name} to channel ID={channel.id}, Name={channel.name} for user {user_id}") # Added log
        question_msg = await channel.send(question_text, view=view)
        survey.current_question_message_id = question_msg.id # Store message ID for cleanup
        survey.current_message = question_msg # Store the message object
        logger.info(f"Sent question for step {step_name} (msg ID: {question_msg.id}) for channel {channel.id}")
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
                await continue_survey(bot, channel, survey) # Pass bot instance
            except Exception as e2:
                logger.error(f"Error continuing survey after step failure: {e2}")
async def continue_survey(bot: commands.Bot, channel: discord.TextChannel, survey: SurveyFlow) -> None: # Added bot parameter, Type hint updated
    """Continues the survey to the next step or finishes it."""
    logger.info(f"[{survey.session_id}] - Entering continue_survey. is_done(): {survey.is_done()}, Current index: {survey.current_index}, Total steps: {len(survey.steps)}") # Added log

    # Fetch the latest survey state using channel_id
    current_survey = survey_manager.get_survey(str(channel.id))
    if not current_survey:
        logger.warning(f"[{survey.session_id}] - Survey not found in continue_survey for channel {channel.id}. Aborting.")
        return

    if current_survey.is_done():
        logger.info(f"[{survey.session_id}] - Survey is done, calling finish_survey.") # Added log
        await finish_survey(bot, channel, current_survey) # Pass bot instance
    else:
        # Remove reaction from the previous message before asking the next step
        if current_survey.current_message:
            try:
                await current_survey.current_message.remove_reaction("⏳", bot.user)
            except Exception as reaction_error:
                logger.warning(f"Could not remove ⏳ reaction from message {current_survey.current_message.id} in channel {channel.id}: {reaction_error}")

        next_step = current_survey.current_step()
        if next_step:
            logger.info(f"[{survey.session_id}] - Asking next step: {next_step}") # Added log
            await ask_dynamic_step(bot, channel, current_survey, next_step) # Pass bot instance
        else:
            # This case should ideally not be reached if is_done() is False but current_step() is None
            logger.error(f"[{survey.session_id}] - Survey not done but no next step found. Finishing survey.") # Added log
            await finish_survey(bot, channel, current_survey) # Pass bot instance

async def finish_survey(bot: commands.Bot, channel: discord.TextChannel, survey: SurveyFlow) -> None: # Added bot parameter, Type hint updated
    """Finalizes a completed survey.
    Sends the collected results in a 'complete' status webhook to n8n
    and cleans up the survey session.
    """
    # Fetch the latest survey state using channel_id
    current_survey = survey_manager.get_survey(str(channel.id))
    if not current_survey or not current_survey.is_done():
        return

    logger.info(f"[{current_survey.session_id}] - Entering finish_survey. is_done(): {current_survey.is_done()}, Current index: {current_survey.current_index}, Total steps: {len(current_survey.steps)}") # Log state in finish_survey
    try:
        # Validate completion data
        if not current_survey or not current_survey.user_id or not current_survey.channel_id:
            raise ValueError("Invalid survey completion data")

        # Send initial completion message
        completion_message = await channel.send(f"{Strings.SURVEY_COMPLETE_MESSAGE}")
        logger.info(f"[{current_survey.session_id}] - Sent initial completion message (ID: {completion_message.id}) to channel {current_survey.channel_id}.")

        payload = {
            "command": "survey",
            "status": "end",
            "userId": current_survey.user_id,
            "channelId": current_survey.channel_id,
            "sessionId": current_survey.session_id, # Added session_id
            "results": current_survey.results
        }
        headers = {"Authorization": f"Bearer {Config.WEBHOOK_AUTH_TOKEN}"}
        logger.info(f"[{current_survey.session_id}] - Sending 'end' status webhook to n8n with payload: {payload}")
        success, data = await webhook_service.send_webhook_with_retry(channel, payload, headers)
        logger.info(f"[{current_survey.session_id}] - 'end' status webhook response: success={success}, data={data}")

        # Process n8n Response & Handle Notion ToDo Fetching
        # Process n8n Response & Handle Notion ToDo Fetching
        if success and data and "url" in data: # Check for 'url' key in response data
            # The URL from n8n should not be sent to the user in the completion message.
            # The initial completion message will remain unless Notion tasks are found and appended.

            # Notion handling block
            notion_url = data["url"] # Use 'url' key
            logger.info(f"[{current_survey.session_id}] - Notion URL found: {notion_url}. Attempting to fetch ToDos for channel {current_survey.channel_id}.")
            try: # Nested try block for specific Notion task fetching/processing errors
                notion_todos_instance = Notion_todos(notion_url, 21)
                logger.info(f"[{current_survey.session_id}] - Calling get_tasks_text for URL: {notion_url}") # Added log before call
                todos_data_str = await notion_todos_instance.get_tasks_text(user_id=current_survey.user_id) # Renamed variable to indicate it's a string
                
                # Parse the JSON string into a dictionary
                todos_data = json.loads(todos_data_str) # Added JSON parsing
                # Only update message if tasks were found
                if isinstance(todos_data, dict) and todos_data.get('tasks_found', False):
                    formatted_todos = todos_data.get('text', '')
                    if formatted_todos:
                        # Calculate remaining allowed characters for the appended tasks
                        # Discord message limit is 2000 characters
                        max_append_length = 2000 - len(completion_message.content) - 2 # 2 for the \n\n

                        # Truncate formatted_todos if it exceeds the limit
                        if len(formatted_todos) > max_append_length:
                            # Leave space for a truncation message
                            truncated_length = max_append_length - len("... (truncated)")
                            if truncated_length < 0: # Ensure truncated_length is not negative
                                truncated_length = 0
                            formatted_todos = formatted_todos[:truncated_length] + "... (truncated)"
                        # Append Notion tasks to the initial completion message
                        updated_content = f"{completion_message.content}\n{formatted_todos}"
                        await completion_message.edit(content=updated_content)
                        logger.info(f"[{current_survey.session_id}] - Appended Notion ToDos to completion message {completion_message.id} in channel {current_survey.channel_id}.")
                    logger.info(f"[{current_survey.session_id}] - No Notion ToDos found.")

            except Exception as inner_notion_e: # Catch specific errors from fetching/processing
                logger.error(f"[{current_survey.session_id}] - Error during Notion task fetching/processing: {inner_notion_e}", exc_info=True)
                # Optionally send a more specific error message to the channel
                try:
                    logger.warning(f"[{current_survey.session_id}] - Помилка при обробці завдань з Notion: {inner_notion_e}")
                except Exception as send_error:
                    logger.error(f"Failed to send inner Notion error message: {send_error}")


        else:
            logger.warning(f"[{current_survey.session_id}] - 'end' status webhook failed or returned no output or no URL. Keeping default completion message.")
            # The initial completion message remains as is.

        # Log completion processing finished
        logger.info(f"[{current_survey.session_id}] - Survey completion processing finished for channel {current_survey.channel_id}. Results: {current_survey.results}")


    except ValueError as ve:
        logger.error(f"[{current_survey.session_id if current_survey else 'N/A'}] - Data validation error during finish_survey: {ve}")
        # Attempt to send a generic error message to the channel
        if channel:
            try:
                await channel.send(f"<@{current_survey.user_id if current_survey else 'N/A'}> {Strings.SURVEY_FINISH_ERROR}: Invalid data.")
            except Exception as send_error:
                logger.error(f"Failed to send validation error message: {send_error}")

    except Exception as e:
        logger.error(f"[{current_survey.session_id if current_survey else 'N/A'}] - Unexpected error during finish_survey: {e}", exc_info=True)
        # Attempt to send a generic error message to the channel
        if channel:
            try:
                await channel.send(f"<@{current_survey.user_id if current_survey else 'N/A'}> {Strings.SURVEY_FINISH_ERROR}: Unexpected error.")
            except Exception as send_error:
                logger.error(f"Failed to send unexpected error message: {send_error}")

    finally:
        # Clean up the survey session
        if current_survey: # Ensure current_survey exists before trying to remove
             survey_manager.remove_survey(current_survey.channel_id)
             logger.info(f"[{current_survey.session_id}] - Survey session removed for channel {current_survey.channel_id}.")