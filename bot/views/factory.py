from typing import Optional, Union
import discord
from config import logger, ViewType
from bot.views.workload import create_workload_view
from bot.views.day_off import create_day_off_view

def create_view(
    view_name: str, 
    cmd_or_step: str,
    user_id: str,
    view_type: ViewType = ViewType.SLASH,
    has_survey: bool = False,
    **kwargs
) -> Union[discord.ui.View, None]:
    """Create appropriate view based on parameters"""
    
    # Survey view handling (button-based implementation)
    if view_name == "survey":
        from bot.views.generic import create_survey_view
        return create_survey_view(cmd_or_step, user_id, **kwargs)
    
    logger.info(f"Creating {view_name} view for command: {cmd_or_step}")
    
    if view_name == "workload":
        return create_workload_view(cmd_or_step, user_id, **kwargs)
    elif view_name == "day_off":
        return create_day_off_view(cmd_or_step, user_id, **kwargs)
        
    return discord.ui.View()