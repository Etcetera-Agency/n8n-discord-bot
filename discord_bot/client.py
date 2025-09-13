from discord.ext import commands
from services.logging_utils import get_logger

def create_bot() -> commands.Bot:
    """Return the shared bot instance constructed in bot.py.

    This preserves existing behavior, prefixes, event handlers,
    and any side-effectful setup performed in that module.
    """
    # Import lazily to avoid circular imports at module import time
    from bot import bot as _bot

    get_logger("bot.client").info("create_bot: return shared instance")
    return _bot
