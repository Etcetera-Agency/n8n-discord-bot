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
events.setup(bot)

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
# Discord on_message Event
###############################################################################
@bot.event
async def on_message(message: discord.Message):
    if message.author == bot.user:
        return

    if bot.user in message.mentions:
        # Add processing reaction
        await message.add_reaction("⏳")
        
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
        await message.add_reaction("✅" if success else "❌")

    if message.content.startswith("start_daily_survey"):
        parts = message.content.split()
        if len(parts) >= 4:
            user_id = parts[1]
            channel_id = parts[2]
            steps = parts[3:]
            await handle_start_daily_survey(bot, user_id, channel_id, steps)

    await bot.process_commands(message)

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
