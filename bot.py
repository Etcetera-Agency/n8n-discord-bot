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
from discord_bot.commands.prefix import PrefixCommands
from discord_bot.commands.slash import SlashCommands
from discord_bot.commands.events import EventHandlers # Assuming EventHandlers setup is needed
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
##############################################################################

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
###############################################################################
###############################################################################
# Discord on_message Event
##############################################################################
@bot.event # Re-added @bot.event decorator
@bot.event
async def on_message(message: discord.Message):
    logger.info(f"on_message triggered for message: {message.content}")
    # Ignore messages from the bot itself
    if message.author == bot.user:
        logger.info("Ignoring message from bot user")
        return
    # Handle messages where the bot is mentioned
    if bot.user in message.mentions:
        logger.info("Bot mentioned in message, attempting to parse command...")

        # Extract content after the mention
        # Find the position after the bot mention
        mention_index = message.content.find(f"<@{bot.user.id}>")
        if mention_index == -1:
             mention_index = message.content.find(f"<@!{bot.user.id}>")

        if mention_index != -1:
            # Adjust slice to account for the length of the mention string found
            mention_string_length = len(f"<@{bot.user.id}>") if message.content[mention_index:].startswith(f"<@{bot.user.id}>") else len(f"<@!{bot.user.id}>")
            content_after_mention = message.content[mention_index + mention_string_length:].strip()

            # Check for known commands after the mention
            if content_after_mention.startswith("!unregister"):
                logger.info(f"Identified !unregister command after mention. Full content after mention: '{content_after_mention}'")
                # Manually create a Context object
                ctx = await bot.get_context(message)
                # Call the unregister command handler directly
                # Assuming prefix_commands instance is accessible in this scope
                await prefix_commands.unregister_cmd(ctx)
                logger.info("unregister_cmd handler called.")
                return # Exit after handling the command

            elif content_after_mention.startswith("!register"):
                 logger.info(f"Identified !register command after mention. Full content after mention: '{content_after_mention}'")
                 # Extract text argument after "!register"
                 text_after_command = content_after_mention[len("!register"):].strip()
                 logger.info(f"Extracted text after !register: '{text_after_command}'")

                 # Manually create a Context object
                 ctx = await bot.get_context(message)
                 # Call the register command handler directly, passing the extracted text
                 await prefix_commands.register_cmd(ctx, text=text_after_command) # Pass text as keyword argument
                 logger.info("register_cmd handler called.")
                 return # Exit after handling the command

            else:
                # If mentioned but no known command follows, proceed with generic mention handling
                logger.info("Bot mentioned but no known command found, proceeding with generic mention handling.")
                # Add processing reaction
                await message.add_reaction(Strings.PROCESSING)

                # Process the message (send webhook for mention)
                success, data = await bot.webhook_service.send_webhook(
                    message,
                    command="mention",
                    message=content_after_mention, # Change from message.content
                    result={}
                )

                # Remove processing reaction
                await message.remove_reaction(Strings.PROCESSING, bot.user)

                # Add success/error reaction
                await message.add_reaction("✅" if success else Strings.ERROR)

                # Send n8n response if available
                if success and data and isinstance(data, list) and len(data) > 0:
                    if isinstance(data[0], dict) and "output" in data[0]:
                        await message.channel.send(str(data[0]["output"]))
                    else:
                        await message.channel.send(str(data))
        else:
             # This case should ideally not happen if bot.user in message.mentions is true,
             # but as a fallback
             logger.warning("Bot mentioned but mention string not found in message content.")
             # Optionally handle as generic mention or ignore

    # Handle other specific message types (if not a mention handled above)
    elif message.content.startswith("start_daily_survey"):
        parts = message.content.split()
        if len(parts) >= 4:
            user_id = parts[1]
            channel_id = parts[2]
            steps = parts[3:]
            await handle_start_daily_survey(bot, user_id, channel_id, steps)

    # Any other general message handling that should happen for non-mention messages would go here.
    # Currently, no other general message handling is needed based on the original code structure.
    pass
# Any other general message handling that should happen for non-command, non-mention messages would go here.



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
