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
    WebhookService,
    Strings # Added Strings
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

# Import command handlers
from bot.commands.prefix import PrefixCommands # Added import

# Import and setup event handlers
from bot.commands import events
events.setup(bot) # Uncommented events setup

# Import and register survey button handler
from bot.commands.survey import SurveyButtonView
bot.add_view(SurveyButtonView())

# Initialize prefix commands
prefix_commands = PrefixCommands(bot)

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
            status="end", # Added status="end"
            result=survey.results[survey.steps[-1]] # Changed result to send only the last step's result
        )
    survey_manager.remove_survey(survey.user_id)

###############################################################################
# UI Component Factory
###############################################################################

###############################################################################
###############################################################################
# Discord Events
###############################################################################
@bot.event
async def on_ready():
    logger.info(f"Bot connected as {bot.user}")
    logger.info("Prefix commands should be registered now.") # Added log
    # Note: Slash commands are synced separately, usually in on_ready or a setup cog

@bot.event
async def on_close():
    logger.info("Bot shutting down, cleaning up resources")
    # Add any necessary cleanup here

###############################################################################
# Discord on_message Event
##############################################################################
@bot.event # Re-added @bot.event decorator
async def on_message(message: discord.Message):
    logger.debug(f"on_message triggered by user {message.author} with content: '{message.content}'") # ADDED VERY FIRST LOG
    if message.author == bot.user:
        logger.debug("on_message: Ignoring message from self.") # Log self-ignore
        return

    if bot.user in message.mentions:
        # Add processing reaction
        await message.add_reaction(Strings.PROCESSING)

        # Process the message
        success, _ = await bot.webhook_service.send_webhook(
            message,
            command="mention",
            message=message.content,
            result={}
        )

        # Remove processing reaction
        await message.remove_reaction(Strings.PROCESSING, bot.user)

        # Add success or error reaction
        await message.add_reaction("✅" if success else Strings.ERROR)

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

###############################################################################
# SLASH COMMANDS
###############################################################################

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
