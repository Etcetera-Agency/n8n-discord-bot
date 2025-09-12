import discord
from discord.ext import commands
from config import logger
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
    
    # Initialize webhook service (internal dispatcher; no HTTP init required)
    bot.webhook_service = WebhookService()
    
    # Register commands and event handlers (side-effectful constructors)
    _ = PrefixCommands(bot)
    _ = SlashCommands(bot)
    _ = EventHandlers(bot)
    
    logger.info("Bot client created and configured")
    return bot
