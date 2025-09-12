from discord.ext import commands
from config import logger

def create_bot() -> commands.Bot:
    """Return the shared bot instance constructed in bot.py.

    This preserves existing behavior, prefixes, event handlers,
    and any side-effectful setup performed in that module.
    """
    # Import lazily to avoid circular imports at module import time
    from bot import bot as _bot

    logger.info("create_bot: returning bot instance from bot.py")
    return _bot
