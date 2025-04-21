import discord
from discord.ext import commands
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
        # Ensure on_message listener is NOT added here

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

    # Removed the on_message handler from this class to avoid duplication
    # The primary on_message handler is now in bot.py