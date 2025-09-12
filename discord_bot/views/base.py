import logging
from typing import Optional, Dict, Any

import discord
from services import session_manager

logger = logging.getLogger(__name__)

class BaseView(discord.ui.View):
    """
    Base view class for all UI components.
    Provides common functionality for all views.
    """
    def __init__(
        self,
        cmd_or_step: str,
        user_id: str,
        timeout: Optional[int] = None,
        has_survey: bool = False
    ):
        """
        Initialize the base view.
        
        Args:
            cmd_or_step: Command or survey step name
            user_id: Discord user ID
            timeout: View timeout in seconds
            has_survey: Whether this view is part of a survey
        """
        super().__init__(timeout=timeout)
        self.cmd_or_step = cmd_or_step
        self.user_id = user_id
        self.session_id = session_manager.get_session_id(user_id)
        self.has_survey = has_survey
        self.data: Dict[str, Any] = {}  # Store all selected data here
    
    def disable_all_items(self) -> None:
        """Disable all items in the view."""
        for item in self.children:
            item.disabled = True
    async def on_timeout(self) -> None:
        """Handle view timeout."""
        logger.debug(f"on_timeout called for {self.cmd_or_step}, has_survey: {self.has_survey}")
        from services import survey_manager
        
        if self.has_survey:
            # Get the survey and handle incomplete steps
            survey = survey_manager.get_survey(self.user_id)
            if survey:
                from bot.commands.survey import handle_survey_incomplete
                await handle_survey_incomplete(self.user_id)
                
        self.disable_all_items()
        self.stop()
