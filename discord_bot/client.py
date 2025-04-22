import discord
from discord.ext import commands
import asyncio
from config import Config, logger
from discord_bot.commands import PrefixCommands, SlashCommands, EventHandlers
from services.webhook import WebhookService

def create_bot() -> commands.Bot:
    """
    Create and configure the Discord bot.
    
    Returns:
        A configured Discord bot instance
    """
    # Set up intents
    intents = discord.Intents.default()
    intents.message_content = True
    
    # Create bot instance
    bot = commands.Bot(command_prefix="!", intents=intents)
    
    # Initialize webhook service
    bot.webhook_service = WebhookService()
    asyncio.create_task(bot.webhook_service.initialize())
    
    # Register commands and event handlers
    prefix_commands = PrefixCommands(bot)
    slash_commands = SlashCommands(bot)
    event_handlers = EventHandlers(bot)
    
    logger.info("Bot client created and configured")
    return bot