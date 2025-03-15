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
    channel = await bot_instance.fetch_channel(int(channel_id))
    if not channel:
        logger.warning(f"Channel {channel_id} not found for user {user_id}")
        return

    survey = survey_manager.create_survey(user_id, channel_id, steps)
    step = survey.current_step()
    if step:
        await ask_dynamic_step(channel, survey, step)
    else:
        await channel.send(f"<@{user_id}> Не вказано кроків опитування.")

async def ask_dynamic_step(channel: discord.TextChannel, survey: 'survey_manager.SurveyFlow', step_name: str) -> None:
    """
    Ask a dynamic survey step.
    
    Args:
        channel: Discord text channel
        survey: Survey flow instance
        step_name: Step name
    """
    user_id = survey.user_id
    if step_name.startswith("workload") or step_name.startswith("connects"):
        if step_name == "workload_nextweek":
            text_q = f"<@{user_id}> Скільки годин на НАСТУПНИЙ тиждень?"
        elif step_name == "workload_thisweek":
            text_q = f"<@{user_id}> Скільки годин на ЦЬОГО тижня?"
        elif step_name == "connects_thisweek":
            text_q = f"<@{user_id}> Скільки CONNECTS на ЦЬОГО тижня?"
        else:
            text_q = f"<@{user_id}> Будь ласка, оберіть кількість годин:"
        view = create_view("workload", step_name, user_id, ViewType.DYNAMIC)
        await channel.send(text_q, view=view)
    elif step_name.startswith("day_off"):
        text_q = f"<@{user_id}> Які дні вихідних на наступний тиждень?"
        view = create_view("day_off", step_name, user_id, ViewType.DYNAMIC)
        await channel.send(text_q, view=view)
    else:
        await channel.send(f"<@{user_id}> Невідомий крок опитування: {step_name}. Пропускаємо.")
        survey.next_step()
        await continue_survey(channel, survey)

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
        await webhook_service.send_webhook(
            channel,
            command="survey",
            result={"final": survey.results}
        )
        logger.info(f"Survey completed for user {survey.user_id} with results: {survey.results}")
    
    survey_manager.remove_survey(survey.user_id) 