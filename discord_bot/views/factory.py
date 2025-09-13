from typing import Optional, Union
import discord
from services.logging_utils import get_logger
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

    get_logger("view.factory", {"userId": user_id}).info(
        "create view", extra={"view": view_name, "cmd_or_step": cmd_or_step}
    )

    # Handle connects_thisweek slash command case explicitly
    if cmd_or_step == "connects_thisweek":
        get_logger("view.factory", {"userId": user_id}).debug(
            "connects_thisweek: no view needed"
        )
        return None

    # Create workload views for slash commands
    if cmd_or_step in ["workload_today", "workload_nextweek"]:
        get_logger("view.factory", {"userId": user_id}).debug(
            "create workload view", extra={"cmd": cmd_or_step}
        )
        try:
            view = create_workload_slash_view(cmd_or_step, user_id, timeout=timeout)
            return view
        except Exception:
            get_logger("view.factory", {"userId": user_id}).exception(
                "error creating workload view", extra={"cmd": cmd_or_step}
            )
            return discord.ui.View(timeout=timeout)
    
    # Create day off views
    if view_name == "day_off":
        get_logger("view.factory", {"userId": user_id}).debug(
            "create day_off view", extra={"cmd": cmd_or_step}
        )
        try:
            view = create_day_off_view(cmd_or_step, user_id, timeout=timeout)
            return view
        except Exception:
            get_logger("view.factory", {"userId": user_id}).exception("error creating day_off view")
            raise
    
    # Default empty view
    return discord.ui.View(timeout=timeout)
