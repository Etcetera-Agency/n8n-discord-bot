import asyncio
import discord
from typing import Optional, List
from config import ViewType, logger, Strings, Config
from services import survey_manager, webhook_service
from bot.views.factory import create_view

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
    
    # Check if steps are provided and non-empty
    steps = data.get("steps", ["workload_today", "workload_nextweek", "connects", "dayoff_nextweek"])
    if len(steps) == 0:
        channel = await bot_instance.fetch_channel(channel_id)
        if channel:
            await channel.send(f"<@{user_id}> {Strings.SURVEY_COMPLETE_MESSAGE}")
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

        # Create survey and start immediately
        survey = survey_manager.create_survey(user_id, channel_id, steps)  # Let SurveyManager handle session_id internally
        logger.info(f"Created survey for channel {channel_id} with steps: {steps}")

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
    Ask a dynamic survey step.
    
    Args:
        channel: Discord text channel
        survey: Survey flow instance
        step_name: Step name
    """
    user_id = survey.user_id
    logger.info(f"Asking step {step_name} for user {user_id} in channel {channel.id}")
    
    try:
        # Create new message for each step
        # Initialize step
        initial_msg = None
        survey.current_message = None

        if step_name.startswith("workload") or step_name.startswith("connects"):
            if step_name == "workload_nextweek":
                text_q = f"<@{user_id}> Скільки годин підтверджено на НАСТУПНИЙ тиждень?"
            elif step_name == "workload_thisweek":
                text_q = f"<@{user_id}> Скільки годин на ЦЬОГО тижня?"
            elif step_name == "workload_today":
                text_q = f"<@{user_id}> Скільки годин на СЬОГОДНІ?"
            elif step_name == "connects_thisweek":
                text_q = f"<@{user_id}> Скільки CONNECTS Upwork Connects History показує ЦЬОГО тижня?\n\nВведіть кількість коннектів що ви бачите на [Upwork Connects History](https://www.upwork.com/nx/plans/connects/history/)"
                logger.info(f"Creating text input for connects_thisweek step")
                initial_msg = await channel.send(text_q)

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
                        if not interaction or str(interaction.channel.id) != str(self.survey.channel_id):
                            if interaction:
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

                modal = ConnectsModal(survey, step_name)
                await channel.send_modal(modal)
            else:
                text_q = f"<@{user_id}> Будь ласка, оберіть кількість годин:"
                
            logger.info(f"Creating workload view for step {step_name}")
            # Send question message
            question_msg = await channel.send(text_q)
            await question_msg.add_reaction("📝")  # Add pencil emoji reaction
            
            # Create view with question message reference
            view = create_view("workload", step_name, user_id, ViewType.DYNAMIC, has_survey=True)
            view.command_msg = question_msg
            
            # Send follow-up message with buttons
            buttons_msg = await channel.send("Оберіть кількість годин:", view=view)
            view.buttons_msg = buttons_msg
            survey.buttons_message = buttons_msg
            
            logger.info(f"Sent workload question for step {step_name}, initial message ID: {initial_msg.id}, buttons message ID: {buttons_msg.id}")
            
            # Send webhook with empty result to notify step started
            # The actual result will be sent when button is pressed in the view
            try:
                if isinstance(channel, discord.TextChannel):
                    # Create a fully initialized dummy interaction with all required attributes
                    class DummyInteraction:
                        def __init__(self, channel, user_id):
                            self.channel = channel
                            self.user = discord.Object(id=int(user_id))
                            self.author = self.user  # Required for Context compatibility
                            self.response = type('Response', (), {
                                'is_done': lambda: False,
                                'defer': lambda *args, **kwargs: None,
                                'send_message': lambda *args, **kwargs: None,
                                'followup': type('Followup', (), {
                                    'send': lambda *args, **kwargs: None
                                })
                            })
                            self.client = type('Client', (), {
                                'user': discord.Object(id=0),
                                'get_user': lambda id: discord.Object(id=id)
                            })
                            self.message = None
                            self.id = str(user_id)  # Required for interaction id
                    
                    dummy_interaction = DummyInteraction(channel, survey.user_id)
                    await webhook_service.send_webhook(
                        dummy_interaction,
                        command=step_name,
                        status="step",
                        result={}
                    )
            except Exception as e:
                logger.error(f"Error sending initial step webhook: {e}")
            
            # Delete buttons message after choice
            if survey.buttons_message:
                await survey.buttons_message.delete()
                survey.buttons_message = None
        elif step_name == "day_off_nextweek":
            text_q = f"<@{user_id}> Які дні вихідних на наступний тиждень?"
            
            logger.info(f"Creating day_off view for step {step_name}")
            # Create and send the view with has_survey=True
            # Send initial message
            initial_msg = await channel.send(text_q)
            
            # Create view with initial message reference
            view = create_view("day_off", step_name, user_id, ViewType.DYNAMIC, has_survey=True)
            view.command_msg = initial_msg
            
            # Send follow-up message with buttons
            buttons_msg = await channel.send("Оберіть дні вихідних:", view=view)
            view.buttons_msg = buttons_msg
            
            logger.info(f"Sent day_off question for step {step_name}, initial message ID: {initial_msg.id}, buttons message ID: {buttons_msg.id}")
            
            # Send webhook without view
            await webhook_service.send_webhook(
                channel,
                command=step_name,
                status="step",
                result={"userId": survey.user_id}
            )
        else:
            logger.warning(f"Unknown step type: {step_name} for user {user_id}")
            await webhook_service.send_webhook(
                channel,
                command=step_name,
                status="error",
                message=f"<@{user_id}> Невідомий крок опитування: {step_name}. Пропускаємо.",
                user_id=user_id
            )
            survey.next_step()
            await continue_survey(channel, survey)
    except Exception as e:
        logger.error(f"Error in ask_dynamic_step for step {step_name}: {e}")
        await channel.send(f"<@{user_id}> {Strings.STEP_ERROR}: {str(e)}")
        # Try to continue with the next step
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
    if survey.is_done():
        try:
            # Create a fully initialized dummy interaction with all required attributes
            class DummyInteraction:
                def __init__(self, channel, user_id):
                    self.channel = channel
                    self.user = discord.Object(id=int(user_id))
                    self.author = self.user  # Required for Context compatibility
                    self.response = type('Response', (), {
                        'is_done': lambda: False,
                        'defer': lambda *args, **kwargs: None,
                        'send_message': lambda *args, **kwargs: None,
                        'followup': type('Followup', (), {
                            'send': lambda *args, **kwargs: None
                        })
                    })
                    self.client = type('Client', (), {
                        'user': discord.Object(id=0),
                        'get_user': lambda id: discord.Object(id=id)
                    })
                    self.message = None
                    self.id = str(user_id)  # Required for interaction id
            
            dummy_interaction = DummyInteraction(channel, survey.user_id)
            await webhook_service.send_webhook(
                dummy_interaction,
                command="survey",
                status="complete",
                result={
                    "final": survey.results,
                    "userId": survey.user_id
                }
            )
            logger.info(f"Survey completed for user {survey.user_id} with results: {survey.results}")
        except Exception as e:
            logger.error(f"Error sending survey completion webhook: {e}")
    
    survey_manager.remove_survey(survey.channel_id)  # Now removing by channel_id