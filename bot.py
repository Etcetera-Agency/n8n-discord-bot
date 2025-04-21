import os
import discord
from discord.ext import commands
from discord import app_commands
import aiohttp
import uuid
import asyncio
import logging
from dotenv import load_dotenv
from cachetools import TTLCache
from typing import Optional, List, Dict, Any, Union, Callable, Tuple
import ssl
from aiohttp import web
from config import Config
from services.session import SessionManager
from services.webhook import WebhookService, initialize_survey_functions
from config import (
    WORKLOAD_OPTIONS,
    WEEKDAY_OPTIONS,
    MONTHS,
    ViewType,
    logger,
    WebhookService
)

###############################################################################
# Logging configuration
###############################################################################
from config.logger import setup_logging
logger = setup_logging()

###############################################################################
# Load environment variables
###############################################################################
load_dotenv()

from config.config import Config

# Global HTTP session for aiohttp requests
http_session = None

###############################################################################
# Global Constants
###############################################################################
###############################################################################
# Response Handler Class
###############################################################################

###############################################################################
# Session and Webhook Helper Functions
###############################################################################

###############################################################################
# Discord Bot Setup
###############################################################################
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Import and setup event handlers
from bot.commands import events
# events.setup(bot) # Temporarily commented out to isolate potential interference

# Import and register survey button handler
from bot.commands.survey import SurveyButtonView
bot.add_view(SurveyButtonView())

###############################################################################
# Survey Management
###############################################################################

async def survey_incomplete_timeout(user_id: str):
    survey = survey_manager.get_survey(user_id)
    if not survey:
        return
    try:
        channel = await bot.fetch_channel(int(survey.channel_id))
        if not channel:
            logger.warning(f"Channel {survey.channel_id} not found for user {user_id}")
            return

        incomplete = survey.incomplete_steps()
        await bot.webhook_service.send_webhook(
            channel,
            command="survey",
            status="incomplete",
            result={"incompleteSteps": incomplete}
        )

        survey_manager.remove_survey(user_id)
    except discord.NotFound:
        logger.error(f"Channel {state.channel_id} not found")
    except discord.Forbidden:
        logger.error(f"Bot doesn't have access to channel {state.channel_id}")
    except Exception as e:
        logger.error(f"Error in survey_incomplete_timeout: {e}")

async def handle_start_daily_survey(bot, user_id: str, channel_id: str, steps: List[str]):
    try:
        channel = await bot.fetch_channel(int(channel_id))
        if not channel:
            logger.warning(f"Channel {channel_id} not found for user {user_id}")
            return

        survey = survey_manager.create_survey(user_id, channel_id, steps)
        step = survey.current_step()
        if step:
            await ask_dynamic_step(channel, survey, step)
        else:
            await channel.send(f"<@{user_id}> -- Схоже всі данні вже занесені")
    except discord.NotFound:
        logger.error(f"Channel {channel_id} not found")
    except discord.Forbidden:
        logger.error(f"Bot doesn't have access to channel {channel_id}")
    except Exception as e:
        logger.error(f"Error in handle_start_daily_survey: {e}")

async def ask_dynamic_step(channel: discord.TextChannel, state: SurveyFlow, step_name: str):
    user_id = state.user_id
    if step_name.startswith("workload") or step_name.startswith("connects"):
        if step_name == "workload_nextweek":
            text_q = f"<@{user_id}> Скільки годин на НАСТУПНИЙ тиждень?"
        elif step_name == "workload_thisweek":
            text_q = f"<@{user_id}> Скільки годин на ЦЬОГО тижня?"
        elif step_name == "connects":
            text_q = f"<@{user_id}> Скільки CONNECTS на ЦЬОГО тижня?"
        else:
            text_q = f"<@{user_id}> Будь ласка, оберіть кількість годин:"
        view = create_view("workload", step_name, user_id, "dynamic")
        await channel.send(text_q, view=view)
    elif step_name.startswith("day_off"):
        text_q = f"<@{user_id}> Які дні вихідних на наступний тиждень?"
        view = create_view("day_off", step_name, user_id, "dynamic")
        await channel.send(text_q, view=view)
    else:
        await channel.send(f"<@{user_id}> Невідомий крок опитування: {step_name}. Пропускаємо.")
        state.next_step()
        nxt = state.current_step()
        if nxt:
            await ask_dynamic_step(channel, state, nxt)
        else:
            await finish_survey(channel, state)

async def finish_survey(channel: discord.TextChannel, survey: SurveyFlow):
    if survey.is_done():
        await bot.webhook_service.send_webhook(
            channel,
            command="survey",
            result={"final": survey.results}
        )
    survey_manager.remove_survey(survey.user_id)

###############################################################################
# UI Component Factory
###############################################################################

###############################################################################
# Discord on_message Event
###############################################################################
@bot.event
async def on_message(message: discord.Message):
    logger.debug(f"on_message triggered by user {message.author} with content: '{message.content}'") # ADDED VERY FIRST LOG
    if message.author == bot.user:
        logger.debug("on_message: Ignoring message from self.") # Log self-ignore
        return

    if bot.user in message.mentions:
        # Add processing reaction
        await message.add_reaction(Config.Strings.PROCESSING)

        # Process the message
        success, _ = await bot.webhook_service.send_webhook(
            message,
            command="mention",
            message=message.content,
            result={}
        )

        # Remove processing reaction
        await message.remove_reaction("⏳", bot.user)

        # Add success or error reaction
        await message.add_reaction("✅" if success else Config.Strings.ERROR)

    if message.content.startswith("start_daily_survey"):
        parts = message.content.split()
        if len(parts) >= 4:
            user_id = parts[1]
            channel_id = parts[2]
            steps = parts[3:]
            await handle_start_daily_survey(bot, user_id, channel_id, steps)
    
    logger.debug(f"Reached end of on_message for message: '{message.content}'. Calling process_commands.") # Added log
    await bot.process_commands(message)

###############################################################################
# PREFIX COMMANDS
###############################################################################
@bot.command(name="register", help="Використання: !register <будь-який текст>")
async def register_cmd(ctx: commands.Context, *, text: str):
    logger.info(f"Attempting !register command from {ctx.author} with text: {text}") # Added log
    await bot.webhook_service.send_webhook(
        ctx,
        command="register",
        result={"text": text}
    )

@bot.command(name="unregister", help="Використання: !unregister")
async def unregister_cmd(ctx: commands.Context):
    logger.info(f"Attempting !unregister command from {ctx.author}") # Added log
    await bot.webhook_service.send_webhook(
        ctx,
        command="unregister",
        result={}
    )

###############################################################################
# SLASH COMMANDS
###############################################################################
day_off_group = app_commands.Group(name="day_off", description=Config.Strings.DAY_OFF_GROUP)

@day_off_group.command(name="thisweek", description=Config.Strings.DAY_OFF_THISWEEK)
async def day_off_thisweek(interaction: discord.Interaction):
    await interaction.response.defer(thinking=True, ephemeral=False)
    view = create_view("day_off", "day_off_thisweek", str(interaction.user.id))
    await interaction.followup.send("Оберіть свої вихідні (цей тиждень), потім натисніть «Відправити»:", view=view, ephemeral=False)

@day_off_group.command(name="nextweek", description=Config.Strings.DAY_OFF_NEXTWEEK)
async def day_off_nextweek(interaction: discord.Interaction):
    await interaction.response.defer(thinking=True, ephemeral=False)
    view = create_view("day_off", "day_off_nextweek", str(interaction.user.id))
    await interaction.followup.send("Оберіть свої вихідні (наступний тиждень), потім натисніть «Відправити»:", view=view, ephemeral=False)

bot.tree.add_command(day_off_group)

@bot.tree.command(name="vacation", description=Config.Strings.VACATION)
@app_commands.describe(
    start_day=Config.Strings.START_DAY,
    start_month=Config.Strings.START_MONTH,
    end_day=Config.Strings.END_DAY,
    end_month=Config.Strings.END_MONTH
)
async def vacation_slash(
    interaction: discord.Interaction,
    start_day: int,
    start_month: str,
    end_day: int,
    end_month: str
):
    # Validate inputs
    if not (1 <= start_day <= 31) or not (1 <= end_day <= 31):
        await interaction.response.send_message(Config.Strings.INVALID_DAY, ephemeral=False)
        return

    # Process vacation request
    await bot.webhook_service.send_webhook(
        interaction,
        command="vacation",
        result={
            "start_day": str(start_day),
            "start_month": start_month,
            "end_day": str(end_day),
            "end_month": end_month
        }
    )
@vacation_slash.autocomplete("start_month")
@vacation_slash.autocomplete("end_month")
async def month_autocomplete(interaction: discord.Interaction, current: str) -> List[app_commands.Choice[str]]:
    current = current.lower()
    return [
        app_commands.Choice(name=month, value=month)
        for month in MONTHS
        if current in month.lower()
    ][:25]  # Limit to 25 choices as per Discord limits

@bot.tree.command(name="workload_today", description=Config.Strings.WORKLOAD_TODAY)
async def slash_workload_today(interaction: discord.Interaction):
    view = create_view("workload", "workload_today", str(interaction.user.id))
    await interaction.response.send_message(f"{Config.Strings.WORKLOAD_TODAY}\nЯкщо нічого, оберіть «Нічого немає».", view=view, ephemeral=False)

@bot.tree.command(name="workload_nextweek", description=Config.Strings.WORKLOAD_NEXTWEEK)
async def slash_workload_nextweek(interaction: discord.Interaction):
    view = create_view("workload", "workload_nextweek", str(interaction.user.id))
    await interaction.response.send_message(f"{Config.Strings.WORKLOAD_NEXTWEEK}\nЯкщо нічого, оберіть «Нічого немає».", view=view, ephemeral=False)

@bot.tree.command(name="connects", description=Config.Strings.CONNECTS)
@app_commands.describe(
    connects=Config.Strings.CONNECTS_PARAM
)
async def slash_connects(interaction: discord.Interaction, connects: int):
    # First defer the response to ensure Discord shows the command usage
    await interaction.response.defer(thinking=True, ephemeral=False)

    logger.info(f"[DEBUG] Connects command from {interaction.user}: {connects}")

    # Get the original message
    message = await interaction.original_response()
    if message:
        await message.add_reaction(Config.Strings.PROCESSING)

    try:
        # Send webhook
        success, data = await bot.webhook_service.send_webhook(
            interaction,
            command="connects",
            result={"connects": connects}
        )
        logger.debug(f"[DEBUG] Webhook response for connects: success={success}, data={data}")

        if message:
            await message.remove_reaction(Config.Strings.PROCESSING, interaction.client.user)

        if success and data and "output" in data:
            await interaction.followup.send(data["output"])
        else:
            error_msg = Config.Strings.CONNECTS_ERROR.format(
                connects=connects,
                error=Config.Strings.GENERAL_ERROR
            )
            if message:
                await message.edit(content=error_msg)
                await message.add_reaction(Config.Strings.ERROR)
            else:
                await interaction.followup.send(error_msg)

    except Exception as e:
        logger.error(f"Error in connects command: {e}")
        if message:
            await message.remove_reaction(Config.Strings.PROCESSING, interaction.client.user)
            error_msg = Config.Strings.CONNECTS_ERROR.format(
                connects=connects,
                error=Config.Strings.UNEXPECTED_ERROR
            )
            await message.edit(content=error_msg)
            await message.add_reaction(Config.Strings.ERROR)

###############################################################################
# Main function to run both the HTTP/HTTPS server and the Discord Bot
###############################################################################
async def main():
    # Start HTTP server
    from web import server
    server_task = asyncio.create_task(server.run_server(bot))

    # Start Discord bot
    await bot.start(Config.DISCORD_TOKEN)

    # Wait for both tasks
    await server_task
if __name__ == "__main__":
    asyncio.run(main())
