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
from services.survey import SurveyFlow # Import SurveyFlow
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
##############################################################################
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
# --- MOVED FROM bot/client.py START ---
# Set up intents
intents = discord.Intents.default()
intents.message_content = True

# Create bot instance
async def get_custom_prefix(bot, message):
    """Determines the command prefix based on message content."""
    prefixes = ["!"]
    if bot.user in message.mentions:
        prefixes.append(f"<@{bot.user.id}> ") # Add mention as a prefix (with space)
        prefixes.append(f"<@!{bot.user.id}> ") # Add mention with nickname as a prefix (with space)
    return commands.when_mentioned_or(*prefixes)(bot, message) # Use when_mentioned_or to handle mentions and other prefixes

# Create bot instance
bot = commands.Bot(command_prefix=get_custom_prefix, intents=intents)

# Initialize webhook service
# Assuming WebhookService is available in this scope (imported earlier)
bot.webhook_service = WebhookService()
# Start initialization in background (might need adjustment based on WebhookService.initialize)
# Consider if await is needed or if create_task is appropriate here
# For simplicity, let's assume direct call or background task is handled elsewhere/not needed immediately
# asyncio.create_task(bot.webhook_service.initialize()) # Revisit if needed

# Import command handlers
from bot.commands.prefix import PrefixCommands
from bot.commands.slash import SlashCommands
from bot.commands.events import EventHandlers # Assuming EventHandlers setup is needed
# Removed import of SurveyButtonView as it seems unused/incorrectly referenced

# Register commands and event handlers
prefix_commands = PrefixCommands(bot)
slash_commands = SlashCommands(bot)
event_handlers = EventHandlers(bot)
# event_handlers.setup() # Call setup if EventHandlers class requires it

# Removed registration of SurveyButtonView as it seems unused/incorrectly referenced
# bot.add_view(SurveyButtonView()) # Removed this line

logger.info("Bot instance created and handlers initialized in bot.py")
# --- MOVED FROM bot/client.py END ---

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
##############################################################################

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
    # Ignore messages from the bot itself
    if message.author == bot.user:
        return

    # Process commands first
    await bot.process_commands(message)

    # Handle messages where the bot is mentioned (if not already handled as a command)
    if bot.user in message.mentions:
        # Add processing reaction
        await message.add_reaction(Strings.PROCESSING)

        # Process the message (send webhook for mention)
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

    # Handle other specific message types (if not a command and not a mention handled above)
    elif message.content.startswith("start_daily_survey"):
        parts = message.content.split()
        if len(parts) >= 4:
            user_id = parts[1]
            channel_id = parts[2]
            steps = parts[3:]
            await handle_start_daily_survey(bot, user_id, channel_id, steps)

    # No need for a general webhook send here, as it was causing timeouts and is handled for mentions above.
    # If other general message handling is needed, it would go here.


###############################################################################
# Main function to run both the HTTP/HTTPS server and the Discord Bot
##############################################################################
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