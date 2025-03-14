import discord
from typing import Optional
from config import ViewType, VIEW_CONFIGS, logger
from bot.views.workload import create_workload_view
from bot.views.day_off import create_day_off_view

def create_view(
    view_name: str,
    cmd_or_step: str,
    user_id: str,
    view_type: ViewType = ViewType.SLASH
) -> discord.ui.View:
    """
    Factory function to create the appropriate view type.
    
    Args:
        view_name: Type of view to create
        cmd_or_step: Command or survey step name
        user_id: Discord user ID
        view_type: View type (DYNAMIC or SLASH)
        
    Returns:
        A configured discord.ui.View instance
    """
    config = VIEW_CONFIGS.get(view_type, VIEW_CONFIGS[ViewType.SLASH])
    timeout = config.get("timeout")
    has_survey = config.get("has_survey", False)
    
    logger.info(f"Creating {view_name} view for user {user_id}, cmd/step: {cmd_or_step}")
    
    if view_name == "workload":
        return create_workload_view(cmd_or_step, user_id, timeout, has_survey)
    elif view_name == "day_off":
        return create_day_off_view(cmd_or_step, user_id, timeout, has_survey)
    
    # Default empty view
    return discord.ui.View(timeout=timeout) 