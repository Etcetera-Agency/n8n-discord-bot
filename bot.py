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
intents.interactions = True # Explicitly enable interactions intent

# Import EventHandlers class
from bot.commands.events import EventHandlers

# Define custom Bot class
class MyBot(commands.Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Initialize services here, they will be available as bot attributes
        logger.info("MyBot.__init__: Initializing WebhookService...")
        self.webhook_service = WebhookService()
        logger.info("MyBot.__init__: Creating EventHandlers instance...")
        self.event_handler_instance = EventHandlers(self) # Pass self (the bot instance)

    async def setup_hook(self):
        """Handles async setup tasks before the bot logs in."""
        logger.info("MyBot.setup_hook: Starting async setup...")

        # Initialize WebhookService session
        logger.debug("MyBot.setup_hook: Attempting to initialize WebhookService session...")
        await self.webhook_service.initialize()
        logger.info("MyBot.setup_hook: WebhookService initialized.")

        # Setup event handlers
        logger.debug("MyBot.setup_hook: Attempting to call event_handler_instance.setup()...")
        await self.event_handler_instance.setup() # Call setup on the instance stored in the bot
        logger.info("MyBot.setup_hook: Event handlers registered.")

        # Start the web server task (can also be done here)
        from web import server
        self.loop.create_task(server.run_server(self)) # Start server in background
        logger.info("MyBot.setup_hook: Web server task created.")

        # Sync slash commands (optional, often done in on_ready but setup_hook is also suitable)
        try:
             logger.info("MyBot.setup_hook: Syncing slash commands...")
             await self.tree.sync()
             logger.info("MyBot.setup_hook: Slash commands synced!")
        except Exception as e:
             logger.error(f"MyBot.setup_hook: Error syncing slash commands: {e}")

        logger.info("MyBot.setup_hook: Completed.")

# Instantiate the custom bot
bot = MyBot(command_prefix="!", intents=intents)

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
        elif step_name == "connects_thisweek":
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
# Discord on_message Event (REMOVED - Handled by EventHandlers class)
###############################################################################
# The @bot.event for on_message is removed from here because
# it's now handled within the EventHandlers class in bot/commands/events.py,
# which is registered via event_handler_instance.setup() in main().

###############################################################################
# PREFIX COMMANDS
###############################################################################
@bot.command(name="register", help="Використання: !register <будь-який текст>")
async def register_cmd(ctx: commands.Context, *, text: str):
    await bot.webhook_service.send_webhook(
        ctx,
        command="register",
        result={"text": text}
    )

@bot.command(name="unregister", help="Використання: !unregister")
async def unregister_cmd(ctx: commands.Context):
    await bot.webhook_service.send_webhook(
        ctx,
        command="unregister",
        result={}
    )

###############################################################################
# SLASH COMMANDS
###############################################################################
day_off_group = app_commands.Group(name="day_off", description="Команди для вихідних")

@day_off_group.command(name="thisweek", description="Оберіть вихідні на ЦЕЙ тиждень.")
async def day_off_thisweek(interaction: discord.Interaction):
    await interaction.response.defer(thinking=True, ephemeral=False)
    view = create_view("day_off", "day_off_thisweek", str(interaction.user.id))
    await interaction.followup.send("Оберіть свої вихідні (цей тиждень), потім натисніть «Відправити»:", view=view, ephemeral=False)

@day_off_group.command(name="nextweek", description="Оберіть вихідні на НАСТУПНИЙ тиждень.")
async def day_off_nextweek(interaction: discord.Interaction):
    await interaction.response.defer(thinking=True, ephemeral=False)
    view = create_view("day_off", "day_off_nextweek", str(interaction.user.id))
    await interaction.followup.send("Оберіть свої вихідні (наступний тиждень), потім натисніть «Відправити»:", view=view, ephemeral=False)

bot.tree.add_command(day_off_group)

@bot.tree.command(name="vacation", description="Вкажіть день/місяць початку та кінця відпустки.")
@app_commands.describe(
    start_day="День початку відпустки (1-31)",
    start_month="Місяць початку відпустки",
    end_day="День закінчення відпустки (1-31)",
    end_month="Місяць закінчення відпустки"
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
        await interaction.response.send_message("День повинен бути між 1 та 31.", ephemeral=False)
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
    
@bot.tree.command(name="workload_today", description="Скільки годин підтверджено з СЬОГОДНІ до кінця тижня?")
async def slash_workload_today(interaction: discord.Interaction):
    view = create_view("workload", "workload_today", str(interaction.user.id))
    await interaction.response.send_message("Скільки годин підтверджено з СЬОГОДНІ до кінця тижня?\nЯкщо нічого, оберіть «Нічого немає».", view=view, ephemeral=False)

@bot.tree.command(name="workload_nextweek", description="Скільки годин підтверджено на НАСТУПНИЙ тиждень?")
async def slash_workload_nextweek(interaction: discord.Interaction):
    view = create_view("workload", "workload_nextweek", str(interaction.user.id))
    await interaction.response.send_message("Скільки годин підтверджено на НАСТУПНИЙ тиждень?\nЯкщо нічого, оберіть «Нічого немає».", view=view, ephemeral=False)

@bot.tree.command(name="connects_thisweek", description="Скільки CONNECTS Upwork Connects History показує ЦЬОГО тижня?")
@app_commands.describe(
    connects="Кількість Upwork Connects, що залишилось на цьому тижні"
)
async def slash_connects_thisweek(interaction: discord.Interaction, connects: int):
    # First defer the response to ensure Discord shows the command usage
    await interaction.response.defer(thinking=True, ephemeral=False)
    
    # Then handle the response through the standard handler
    await bot.webhook_service.send_webhook(
        interaction,
        command="connects_thisweek",
        result={"connects": connects}
    )

###############################################################################
# Main function (REMOVED - Replaced by setup_hook and bot.run)
###############################################################################

if __name__ == "__main__":
    logger.info("Starting bot using bot.run()...")
    bot.run(Config.DISCORD_TOKEN)
