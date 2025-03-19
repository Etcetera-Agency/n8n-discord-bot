import discord
from typing import Optional, List
from config import ViewType, logger
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
    await webhook_service.send_webhook(
        channel,
        command="survey",
        status="incomplete",
        result={"incompleteSteps": incomplete}
    )
    
    survey_manager.remove_survey(user_id)
    logger.info(f"Survey for user {user_id} timed out with incomplete steps: {incomplete}")

async def handle_start_daily_survey(bot_instance: discord.Client, user_id: str, channel_id: str, steps: List[str]) -> None:
    """
    Start a daily survey for a user.
    
    Args:
        bot_instance: Discord bot instance
        user_id: Discord user ID
        channel_id: Discord channel ID
        steps: List of survey step names
    """
    logger.info(f"Starting daily survey for user {user_id} in channel {channel_id} with steps: {steps}")
    
    try:
        channel = await bot_instance.fetch_channel(int(channel_id))
        if not channel:
            logger.warning(f"Channel {channel_id} not found for user {user_id}")
            return
        
        # Check if there's an existing survey for this user
        existing_survey = survey_manager.get_survey(user_id)
        if existing_survey:
            logger.info(f"Found existing survey for user {user_id}, removing it")
            survey_manager.remove_survey(user_id)
        
        # Create a new survey
        survey = survey_manager.create_survey(user_id, channel_id, steps)
        logger.info(f"Created survey for user {user_id} with steps: {steps}")
        
        # Get the first step
        step = survey.current_step()
        if step:
            logger.info(f"Starting first step: {step} for user {user_id}")
            await ask_dynamic_step(channel, survey, step)
        else:
            logger.warning(f"No steps provided for user {user_id}")
            await channel.send(f"<@{user_id}> Не вказано кроків опитування.")
    except Exception as e:
        logger.error(f"Error in handle_start_daily_survey: {e}")
        # Try to send an error message to the channel
        try:
            channel = await bot_instance.fetch_channel(int(channel_id))
            await channel.send(f"<@{user_id}> Помилка при запуску опитування: {str(e)}")
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
        if step_name.startswith("workload") or step_name.startswith("connects"):
            if step_name == "workload_nextweek":
                text_q = f"<@{user_id}> Скільки годин на НАСТУПНИЙ тиждень?"
            elif step_name == "workload_thisweek":
                text_q = f"<@{user_id}> Скільки годин на ЦЬОГО тижня?"
            elif step_name == "workload_today":
                text_q = f"<@{user_id}> Скільки годин на СЬОГОДНІ?"
            elif step_name == "connects_thisweek":
                text_q = f"<@{user_id}> Скільки CONNECTS на ЦЬОГО тижня?"
            else:
                text_q = f"<@{user_id}> Будь ласка, оберіть кількість годин:"
                
            logger.info(f"Creating workload view for step {step_name}")
            # Create and send the view with has_survey=True
            # Send initial message
            initial_msg = await channel.send(text_q)
            
            # Create view with initial message reference
            view = create_view("workload", step_name, user_id, ViewType.DYNAMIC, has_survey=True)
            view.command_msg = initial_msg
            
            # Send follow-up message with buttons
            buttons_msg = await channel.send("Оберіть кількість годин:", view=view)
            view.buttons_msg = buttons_msg
            
            logger.info(f"Sent workload question for step {step_name}, initial message ID: {initial_msg.id}, buttons message ID: {buttons_msg.id}")
            
            # Send webhook without view
            await webhook_service.send_webhook(
                channel,
                command=step_name,
                result={}
            )
        elif step_name.startswith("day_off"):
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
                result={}
            )
        else:
            logger.warning(f"Unknown step type: {step_name} for user {user_id}")
            await webhook_service.send_webhook(
                channel,
                command=step_name,
                status="error",
                message=f"<@{user_id}> Невідомий крок опитування: {step_name}. Пропускаємо."
            )
            survey.next_step()
            await continue_survey(channel, survey)
    except Exception as e:
        logger.error(f"Error in ask_dynamic_step for step {step_name}: {e}")
        await channel.send(f"<@{user_id}> Помилка при запуску кроку {step_name}: {str(e)}")
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
    next_step = survey.current_step()
    if next_step:
        await ask_dynamic_step(channel, survey, next_step)
    else:
        await finish_survey(channel, survey)

async def finish_survey(channel: discord.TextChannel, survey: 'survey_manager.SurveyFlow') -> None:
    """
    Finish a survey and send the results.
    
    Args:
        channel: Discord text channel
        survey: Survey flow instance
    """
    if survey.is_done():
        await webhook_service.send_interaction_response(
            channel,
            initial_message="Завершення опитування...",
            command="survey",
            result={"final": survey.results}
        )
        logger.info(f"Survey completed for user {survey.user_id} with results: {survey.results}")
    
    survey_manager.remove_survey(survey.user_id) 