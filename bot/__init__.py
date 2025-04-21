# The bot instance is now in bot_instance.py at the root level.
# main.py imports it directly from there.
# We no longer need to expose the root bot instance through this package's __init__.py.

# You might still need to import/export other components within the bot package here
# if they are used elsewhere in the project.
# Example: from .client import create_bot
# Example: from .commands.prefix import PrefixCommands

# For now, let's clear out the problematic import.
# If other parts of the code rely on imports from bot.__init__, they might need adjustment.

__all__ = [] # Clear __all__ for now, add back if needed