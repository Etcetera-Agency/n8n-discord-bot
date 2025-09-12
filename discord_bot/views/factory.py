from typing import Optional, Union
import discord
from config import logger
from .workload_slash import create_workload_view as create_workload_slash_view
from .day_off_slash import create_day_off_view

def create_view(
    bot_instance,
    view_name: str,
    cmd_or_step: str,
    user_id: str,
    timeout: Optional[float] = None
) -> Union[discord.ui.View, discord.ui.Modal]:
    """
    Factory function to create the appropriate view type.
    """

    logger.info(f"Creating {view_name} view for command: {cmd_or_step}")

    # Handle connects_thisweek slash command case explicitly
    if cmd_or_step == "connects_thisweek":
        logger.debug(f"[{user_id}] - create_view called for connects_thisweek slash command. Returning None as no view is needed.")
        return None

    # Create workload views for slash commands
    if cmd_or_step in ["workload_today", "workload_nextweek"]:
        logger.debug(f"[{user_id}] - Creating workload SLASH view for: {cmd_or_step}")
        try:
            view = create_workload_slash_view(cmd_or_step, user_id, timeout=timeout)
            return view
        except Exception as e:
            logger.error(f"[{user_id}] - Error creating workload SLASH view: {e}", exc_info=True)
            return discord.ui.View(timeout=timeout)
    
    # Create day off views
    if view_name == "day_off":
        logger.debug(f"Creating day_off view for {cmd_or_step}, user {user_id}")
        try:
            view = create_day_off_view(cmd_or_step, user_id, timeout=timeout)
            return view
        except Exception as e:
            logger.error(f"Error creating day_off view: {e}")
            raise
    
    # Default empty view
    return discord.ui.View(timeout=timeout)