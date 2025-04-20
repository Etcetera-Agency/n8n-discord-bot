import asyncio
import discord
from typing import Optional, List
from config import ViewType, logger, Strings, Config
from services import survey_manager, webhook_service
from bot.views.factory import create_view, WorkloadTodayModal, WorkloadNextWeekModal, DayOffNextWeekModal

class SurveyButtonView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)  # Persistent view
    
    @discord.ui.button(custom_id="survey_step_*")
    async def handle_survey_step(self, interaction: discord.Interaction, button: discord.ui.Button):
        logger.info(f"Survey step button clicked: {interaction.data}")
        try:
            # Parse survey ID and step name from custom_id
            _, survey_id, step_name = interaction.data["custom_id"].split("_")
            
            # Get survey from manager
            survey = survey_manager.get_survey(survey_id)
            if not survey:
                await interaction.response.send_message(
                    Strings.SURVEY_START_ERROR,
                    ephemeral=True
                )
                return
            
            # Verify channel match
            if str(interaction.channel.id) != str(survey.channel_id):
                await interaction.response.send_message(
                    "Це опитування не для цього каналу.",
                    ephemeral=True
                )
                return
            
            # Create appropriate modal
            modals = {
                "workloadtoday": WorkloadTodayModal,
                "workloadnextweek": WorkloadNextWeekModal,
                "dayoffnextweek": DayOffNextWeekModal,
                "connects": None  # Handled separately
            }
            
            ModalClass = modals.get(step_name.lower())
            if ModalClass:
                await interaction.response.send_modal(
                    ModalClass(survey, step_name)
                )
            else:
                await interaction.response.send_message(
                    Strings.INVALID_STEP_MESSAGE,
                    ephemeral=True
                )
                
        except Exception as e:
            logger.error(f"Error handling survey button: {e}")
            await interaction.response.send_message(
                Strings.GENERAL_ERROR,
                ephemeral=True
            )

async def handle_survey_incomplete(user_id: str) -> None:
    """
    Handle incomplete survey timeout.
    
    Args:
        user_id: Discord user ID
    """
    survey = survey_manager.get_survey(user_id)
    if not survey:
        return
        
    channel = discord.utils.get(discord.utils.get_all_channels(), id=int(survey.channel_id))
    if not channel:
        logger.warning(f"Channel {survey.channel_id} not found for user {user_id}")
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
    
    survey_manager.remove_survey(user_id)
    logger.info(f"Survey for user {user_id} timed out with incomplete steps: {incomplete}")

async def handle_start_daily_survey(bot_instance: discord.Client, user_id: str, channel_id: str, session_id: str, steps: List[str]) -> None:
    """
    Start a daily survey for a user.

    Args:
        bot_instance: Discord bot instance
        user_id: Discord user ID
        channel_id: Discord channel ID
        steps: List of survey step names
    """
    logger.info(f"Starting daily survey for user {user_id} in channel {channel_id}")
    
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

    try:
        channel = await bot_instance.fetch_channel(int(channel_id))
        if not channel:
            logger.warning(f"Channel {channel_id} not found for user {user_id}")
            return

        # Check if there's an existing survey for this user and remove it
        existing_survey = survey_manager.get_survey(user_id)
        if existing_survey:
            logger.info(f"Found existing survey for user {user_id}, removing it before sending start button")
            survey_manager.remove_survey(user_id)

        # Send persistent start button (survey object will be created on button press)


        # Verify channel with n8n and get steps
        payload = {
            "command": "check_channel",
            "channelId": channel_id
        }
        headers = {"Authorization": f"Bearer {Config.WEBHOOK_AUTH_TOKEN}"}
        success, data = await webhook_service.send_webhook_with_retry(None, payload, headers)
        
        if not success or str(data.get("output", "false")).lower() != "true":
            logger.warning(f"Channel {channel_id} not registered for surveys")
            return

        # Check if steps are provided
        steps = data.get("steps", [])
        if not steps:
            await channel.send(f"<@{user_id}> {Strings.SURVEY_COMPLETE_MESSAGE}")
            return

        # Only allow known step types, skip others silently
        ALLOWED_STEPS = {
            "workload_today": "workload",
            "workload_nextweek": "workload",
            "connects": "connects",
            "dayoff_nextweek": "day_off"
        }
        
        valid_steps = []
        for step in steps:
            if step in ALLOWED_STEPS:
                valid_steps.append(ALLOWED_STEPS[step])
            else:
                logger.debug(f"Skipping invalid step type: {step}")

        if not valid_steps:
            logger.warning(f"No valid steps for user {user_id}")
            return

        survey = survey_manager.create_survey(user_id, channel_id, valid_steps)
        logger.info(f"Created survey with filtered steps: {valid_steps}")

        # Start first step or show completion
        step = survey.current_step()
        if step:
            logger.info(f"Starting first step: {step} for user {user_id}")
            await ask_dynamic_step(channel, survey, step)
        else:
            logger.warning(f"No steps provided for user {user_id}")
            await channel.send(f"<@{user_id}> {Strings.SURVEY_COMPLETE_MESSAGE}")
    except Exception as e:
        logger.error(f"Error in handle_start_daily_survey: {e}")
        # Try to send an error message to the channel
        survey = None
        try:
            channel = await bot_instance.fetch_channel(int(channel_id))
            await channel.send(f"<@{user_id}> {Strings.SURVEY_START_ERROR}: {str(e)}")
        except:
            logger.error(f"Could not send error message to channel {channel_id}")

async def ask_dynamic_step(channel: discord.TextChannel, survey: 'survey_manager.SurveyFlow', step_name: str) -> None:
    """
    Ask a dynamic survey step with robust validation.
    
    Args:
        channel: Discord text channel
        survey: Survey flow instance
        step_name: Step name
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
        # Standardized step question format using Strings
        step_questions = {
            "workload_today": Strings.WORKLOAD_TODAY_QUESTION,
            "workload_nextweek": Strings.WORKLOAD_NEXTWEEK_QUESTION,
            "connects": Strings.CONNECTS_QUESTION,
            "day_off_nextweek": Strings.DAY_OFF_NEXTWEEK
        }
        
        question_text = f"<@{user_id}> {step_questions.get(step_name, step_name)}"

        # Check if this is the special connects_thisweek case
        if step_name == "connects_thisweek":
            logger.info(f"Creating text input for connects_thisweek step")
            initial_msg = await channel.send(question_text)
            
            class ConnectsModal(discord.ui.Modal):
                def __init__(self, survey, step_name):
                    super().__init__(title="Введіть кількість коннектів", timeout=120)
                    self.survey = survey
                    self.step_name = step_name
                    self.connects_input = discord.ui.TextInput(
                        label="Кількість коннектів",
                        placeholder="Введіть число",
                        min_length=1,
                        max_length=3
                    )
                    self.add_item(self.connects_input)

                async def on_submit(self, interaction: discord.Interaction):
                    logger.info(f"ConnectsModal submit - interaction: {type(interaction)}, channel: {getattr(interaction, 'channel', None)}")
                    if not interaction or not hasattr(interaction, 'channel') or str(interaction.channel.id) != str(self.survey.channel_id):
                        logger.error(f"Invalid interaction in ConnectsModal - interaction: {interaction}, channel match: {str(interaction.channel.id) if interaction and hasattr(interaction, 'channel') else 'N/A'} vs {self.survey.channel_id}")
                        if interaction and hasattr(interaction, 'response'):
                            await interaction.response.send_message("Це опитування не для цього каналу.", ephemeral=True)
                        return
                    # Ensure consistent types (string vs int)
                    channel_id = str(interaction.channel.id)
                        
                    if not self.connects_input.value.isdigit():
                        await interaction.response.send_message("Будь ласка, введіть числове значення.", ephemeral=True)
                        return
                        
                    self.survey.results[self.step_name] = int(self.connects_input.value)
                    await interaction.response.send_message(f"Збережено: {self.connects_input.value} коннектів", ephemeral=True)
                    self.survey.next_step()
                    await continue_survey(channel, self.survey)

            if not channel:
                logger.error("Cannot send modal - channel is None")
                return
            if not survey or not hasattr(survey, 'user_id'):
                logger.error("Invalid survey state when creating ConnectsModal")
                return

            logger.info(f"Creating ConnectsModal for step {step_name}, user {survey.user_id}")
            modal = ConnectsModal(survey, step_name)
            await channel.send_modal(modal)
            logger.info(f"Sent modal for step {step_name}")
            # COMPLETELY STOP HERE - Modal will handle continuation after submission
            return

        # Standard step handling - question + button
        class SurveyInputButton(discord.ui.View):
            def __init__(self, survey_id: str, step: str):
                super().__init__(timeout=None)  # Persistent view
                self.custom_id = f"survey_step_{survey_id}_{step}"
                self.add_item(discord.ui.Button(
                    label="Ввести",
                    custom_id=self.custom_id,
                    style=discord.ButtonStyle.primary
                ))
        
        # Send question with input button
        view = SurveyInputButton(survey.session_id, step_name)
        question_msg = await channel.send(question_text, view=view)
        
        # Store message reference in survey
        survey.current_step_message = question_msg
        survey.current_step = step_name
        
        logger.info(f"Sent standardized survey step: {step_name}, message ID: {question_msg.id}")

        # Handle day off steps using standardized question + button
        if step_name == "day_off_nextweek":
            view = SurveyInputButton(survey.session_id, step_name)
            question_msg = await channel.send(question_text, view=view)
            survey.current_step_message = question_msg
            logger.info(f"Sent day off question for step {step_name}, message ID: {question_msg.id}")
            return

        # Handle non-supported step types
        if step_name not in step_questions:
            logger.warning(f"Invalid step type: {step_name} for user {user_id}")
            await channel.send(f"<@{user_id}> {Strings.INVALID_STEP_MESSAGE}")
            return
        else:
            logger.warning(f"Invalid step type: {step_name} for user {user_id}")
            await channel.send(f"<@{user_id}> Invalid survey step configuration")
            # Don't auto-advance or finish - let user restart survey
            return
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

async def continue_survey(channel: discord.TextChannel, survey: 'survey_manager.SurveyFlow') -> None:
    """
    Continue a survey with the next step or finish it.
    
    Args:
        channel: Discord text channel
        survey: Survey flow instance
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


async def finish_survey(channel: discord.TextChannel, survey: 'survey_manager.SurveyFlow') -> None:
    """
    Finish a survey and send the results.
    
    Args:
        channel: Discord text channel
        survey: Survey flow instance
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
            "result": survey.results,
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
        survey_manager.remove_survey(survey.channel_id)