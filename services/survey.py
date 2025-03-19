from typing import Dict, List, Optional, Any
import discord
from config import logger

class SurveyFlow:
    """
    Holds a list of survey steps for dynamic surveys.
    Manages the state of a survey in progress.
    """
    def __init__(self, user_id: str, channel_id: str, steps: List[str]):
        """
        Initialize a new survey flow.
        
        Args:
            user_id: The Discord user ID
            channel_id: The Discord channel ID
            steps: List of survey step names
        """
        self.user_id = user_id
        self.channel_id = channel_id
        self.steps = steps
        self.current_index = 0
        self.results: Dict[str, Any] = {}
        self.current_message: Optional[discord.Message] = None
        self.buttons_message: Optional[discord.Message] = None
        self.start_message: Optional[discord.Message] = None
        logger.info(f"Created survey flow for user {user_id} with steps: {steps}")
        
    async def cleanup(self) -> None:
        """
        Clean up survey messages.
        """
        try:
            if self.buttons_message:
                await self.buttons_message.delete()
            if self.start_message:
                await self.start_message.delete()
        except Exception as e:
            logger.error(f"Error cleaning up survey messages: {e}")

    def current_step(self) -> Optional[str]:
        """
        Get the current step name.
        
        Returns:
            The current step name or None if all steps are completed
        """
        if self.current_index < len(self.steps):
            return self.steps[self.current_index]
        return None

    def next_step(self) -> None:
        """Advance to the next step in the survey."""
        self.current_index += 1
        logger.info(f"Advanced to step {self.current_index} for user {self.user_id}")

    def is_done(self) -> bool:
        """
        Check if the survey is complete.
        
        Returns:
            True if all steps are completed, False otherwise
        """
        return self.current_index >= len(self.steps)

    def incomplete_steps(self) -> List[str]:
        """
        Get a list of incomplete steps.
        
        Returns:
            List of step names that are not yet completed
        """
        return self.steps[self.current_index:] if not self.is_done() else []
        
    def add_result(self, step_name: str, value: Any) -> None:
        """
        Add a result for a step.
        
        Args:
            step_name: The step name
            value: The result value
        """
        self.results[step_name] = value
        logger.info(f"Added result for step {step_name} for user {self.user_id}")


class SurveyManager:
    """
    Manages active surveys across users.
    """
    def __init__(self):
        """Initialize the survey manager."""
        self.surveys: Dict[str, SurveyFlow] = {}
        
    def create_survey(self, user_id: str, channel_id: str, steps: List[str]) -> SurveyFlow:
        """
        Create a new survey for a user.
        
        Args:
            user_id: The Discord user ID
            channel_id: The Discord channel ID
            steps: List of survey step names
            
        Returns:
            The created SurveyFlow instance
        """
        survey = SurveyFlow(user_id, channel_id, steps)
        self.surveys[user_id] = survey
        return survey
        
    def get_survey(self, user_id: str) -> Optional[SurveyFlow]:
        """
        Get an active survey for a user.
        
        Args:
            user_id: The Discord user ID
            
        Returns:
            The SurveyFlow instance or None if not found
        """
        return self.surveys.get(user_id)
        
    def remove_survey(self, user_id: str) -> None:
        """
        Remove a survey for a user.
        
        Args:
            user_id: The Discord user ID
        """
        if user_id in self.surveys:
            del self.surveys[user_id]
            logger.info(f"Removed survey for user {user_id}")

# Global survey manager instance
survey_manager = SurveyManager() 