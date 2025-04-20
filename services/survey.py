from typing import Dict, List, Optional, Any
import discord
from config import logger

class SurveyFlow:
    """
    Holds a list of survey steps for dynamic surveys.
    Manages the state of a survey in progress.
    """
    def __init__(self, channel_id: str, steps: List[str], user_id: str, session_id: str):
        """Initialize survey with required IDs:
        - channel_id: Discord channel ID where survey is running
        - steps: List of survey step names
        - user_id: Discord user ID participating in survey
        - session_id: Combined channel.user ID from initial request
        
        Raises:
            ValueError: If any required ID is missing or invalid"""
        if not channel_id or not user_id or not session_id:
            raise ValueError("channel_id, user_id and session_id are required")
            
        self.user_id = user_id
        self.channel_id = channel_id
        self.steps = steps
        self.session_id = session_id
        self.current_index = 0
        self.results: Dict[str, Any] = {}
        self.current_message: Optional[discord.Message] = None
        self.buttons_message: Optional[discord.Message] = None
        self.start_message: Optional[discord.Message] = None
        self.current_question_message_id: Optional[int] = None
        logger.info(f"Created survey flow for user {user_id} with steps: {steps}")
        
    async def cleanup(self) -> None:
        """
        Clean up survey messages with robust error handling.
        """
        msgs_to_clean = [
            (self.buttons_message, "buttons_message"),
            (self.start_message, "start_message"),
            (None, "question")  # Will try to cleanup by ID if exists
        ]
        
        for msg, msg_type in msgs_to_clean:
            try:
                if msg_type == "question":
                    if not self.current_question_message_id:
                        continue
                    channel = self._get_channel()
                    if channel:
                        msg = await channel.fetch_message(self.current_question_message_id)
                
                if msg:
                    await msg.delete()
                    
                # Reset ID references
                if msg_type == "buttons_message":
                    self.buttons_message = None
                elif msg_type == "start_message":
                    self.start_message = None
                elif msg_type == "question":
                    self.current_question_message_id = None
                    
            except discord.NotFound:
                logger.debug(f"Message {msg_type} was already deleted")
            except discord.Forbidden:
                logger.warning(f"No permissions to delete message {msg_type}")
            except discord.HTTPException as e:
                logger.error(f"HTTP error deleting {msg_type}: {e}")
            except Exception as e:
                logger.error(f"Unexpected error cleaning up {msg_type}: {e}")

    def _get_channel(self) -> Optional[discord.TextChannel]:
        """Get the Discord channel if possible"""
        try:
            client = discord.utils.get(discord.utils.get_all_channels(), id=int(self.channel_id))
            return client if client and isinstance(client, discord.TextChannel) else None
        except Exception:
            return None

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
        
    def create_survey(self, user_id: str, channel_id: str, steps: List[str], session_id: str) -> SurveyFlow:
        """Create and track a new survey instance.
        
        Args:
        user_id: Discord user ID
        channel_id: Discord channel ID
        steps: List of survey step names
        session_id: Combined channel.user ID from initial request
            
        Returns:
            The created SurveyFlow instance
            
        Raises:
            ValueError: If parameters are invalid
        """
        if not all([user_id, channel_id]) or not isinstance(steps, list):
            raise ValueError("Invalid survey parameters")
            
        try:
            survey = SurveyFlow(channel_id, steps, user_id, session_id)
            self.surveys[str(user_id)] = survey
            return survey
        except Exception as e:
            logger.error(f"Failed to create survey: {e}")
            raise ValueError("Survey creation failed") from e
        
    def get_survey(self, user_id: str, channel_id: Optional[str] = None) -> Optional[SurveyFlow]:
        """Get survey by user ID with optional channel validation.
        
        Args:
            user_id: Discord user ID to lookup
            channel_id: Optional channel ID to verify
            
        Returns:
            Matching SurveyFlow or None if not found
        """
        survey = self.surveys.get(str(user_id))
        if not survey:
            return None
            
        if channel_id and str(survey.channel_id) != str(channel_id):
            return None
        return survey
        
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