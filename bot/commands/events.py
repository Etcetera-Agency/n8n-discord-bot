import discord
from discord.ext import commands
import aiohttp
from services.survey import survey_manager
from services.webhook import WebhookService
from config.logger import logger

class EventHandlers:
    def __init__(self, bot):
        """Initialize event handlers with the bot instance"""
        self.bot = bot
        self.http_session = None

    async def setup(self):
        """Register all event handlers with the bot"""
        self.bot.add_listener(self.on_ready)
        self.bot.add_listener(self.on_close)
        self.bot.add_listener(self.on_message)

    async def on_ready(self):
        logger.info(f"Bot connected as {self.bot.user}")
        connector = aiohttp.TCPConnector(limit=10, ttl_dns_cache=300)
        self.http_session = aiohttp.ClientSession(connector=connector)

        # Initialize WebhookService and assign to bot
        self.bot.webhook_service = WebhookService()
        await self.bot.webhook_service.initialize()

        try:
            await self.bot.tree.sync()
            logger.info("Slash commands synced!")
        except Exception as e:
            logger.error(f"Error syncing slash commands: {e}")

    async def on_close(self):
        logger.info("Bot shutting down, cleaning up resources")
        if self.http_session and not self.http_session.closed:
            await self.http_session.close()

    async def on_message(self, message: discord.Message):
        if message.author == self.bot.user:
            return

        if self.bot.user in message.mentions:
            await message.add_reaction("⏳")
            success, _ = await self.bot.webhook_service.send_webhook(
                message,
                command="mention",
                message=message.content,
                result={}
            )
            await message.remove_reaction("⏳", self.bot.user)
            await message.add_reaction("✅" if success else "❌")

        if message.content.startswith("start_daily_survey"):
            parts = message.content.split()
            if len(parts) >= 4:
                user_id = parts[1]
                channel_id = parts[2]
                steps = parts[3:]
                await self.handle_start_daily_survey(user_id, channel_id, steps)

        await self.bot.process_commands(message)