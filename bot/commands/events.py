import discord
from discord.ext import commands
import aiohttp
from services.survey import survey_manager
from services.webhook import WebhookService
from config.logger import logger

class EventHandlers:
    @staticmethod
    async def setup(bot):
        """Register all event handlers with the bot"""
        bot.add_listener(EventHandlers.on_ready)
        bot.add_listener(EventHandlers.on_close)
        bot.add_listener(EventHandlers.on_message)

    @staticmethod
    async def on_ready():
        global http_session
        logger.info(f"Bot connected as {bot.user}")
        connector = aiohttp.TCPConnector(limit=10, ttl_dns_cache=300)
        http_session = aiohttp.ClientSession(connector=connector)

        # Initialize WebhookService and assign to bot
        bot.webhook_service = WebhookService(http_session)
        await bot.webhook_service.initialize()
        
        try:
            await bot.tree.sync()
            logger.info("Slash commands synced!")
        except Exception as e:
            logger.error(f"Error syncing slash commands: {e}")

    @staticmethod
    async def on_close():
        logger.info("Bot shutting down, cleaning up resources")
        if http_session and not http_session.closed:
            await http_session.close()

    @staticmethod
    async def on_message(message: discord.Message):
        if message.author == bot.user:
            return

        if bot.user in message.mentions:
            await message.add_reaction("⏳")
            success, _ = await bot.webhook_service.send_webhook(
                message,
                command="mention",
                message=message.content,
                result={}
            )
            await message.remove_reaction("⏳", bot.user)
            await message.add_reaction("✅" if success else "❌")

        if message.content.startswith("start_daily_survey"):
            parts = message.content.split()
            if len(parts) >= 4:
                user_id = parts[1]
                channel_id = parts[2]
                steps = parts[3:]
                await EventHandlers.handle_start_daily_survey(bot, user_id, channel_id, steps)

        await bot.process_commands(message)