# Import the bot instance from the root bot.py file
from ..bot import bot

# You might still need create_bot if other parts of the code use it,
# but for main.py's import, we need the 'bot' instance exposed.
# from bot.client import create_bot # Keep or remove based on other usage

__all__ = ['bot'] # Expose the bot instance
# If create_bot is still needed elsewhere:
# __all__ = ['bot', 'create_bot']