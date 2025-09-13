from typing import Dict, List, Optional, Any
import discord
from config import logger
from services.survey_models import SurveyStep, SurveyResult

class SurveyFlow:
    """
    Holds a list of survey steps for dynamic surveys and manages
    the state of a survey in progress.

    The optional `client` is a Discord client/bot used only for
    convenience lookups during cleanup (fetching the channel to
    delete prior messages). It is not required for core state logic.
    """
    def __init__(self, channel_id: str, steps: List[SurveyStep], user_id: str, session_id: str, client: Optional[discord.Client] = None):
        # Existing properties
        self.active_view: Optional[discord.ui.View] = None  # Add this
        """Initialize survey with required IDs:
        - channel_id: Discord channel ID where survey is running
        - steps: List of survey step names
        - user_id: Discord user ID participating in survey
        - session_id: Combined channel.user ID from initial request
        """
        logger.debug(f"[{user_id}] - SurveyFlow.__init__ called for user {user_id}, channel {channel_id}, session {session_id} with steps: {steps}") # Added log
        if not channel_id or not user_id or not session_id: # Validate required IDs
            logger.error(f"[{user_id}] - Missing required IDs during SurveyFlow initialization.") # Added log
            raise ValueError("channel_id, user_id and session_id are required")

        self.user_id = user_id
        self.channel_id = channel_id
        # Store explicit step models
        self.steps: List[SurveyStep] = list(steps)
        self.session_id = session_id
        self.current_index = 0
        self.results: Dict[str, SurveyResult] = {}
        self.current_message: Optional[discord.Message] = None # Store the current message object
        self.buttons_message: Optional[discord.Message] = None
        self.start_message: Optional[discord.Message] = None
        self.current_question_message_id: Optional[int] = None
        self.todo_url: Optional[str] = None
        self.client: Optional[discord.Client] = client
        logger.info(f"[{user_id}] - Created survey flow for user {user_id} with steps: {steps}") # Modified log

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
                if msg_type == "question": # Handle cleanup by ID if message object is not stored
                    if not self.current_question_message_id:
                        continue
                    channel = self._get_channel() # Get the channel object
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
                pass # Message was already deleted
            except discord.Forbidden: # Log permission errors
                logger.warning(f"No permissions to delete message {msg_type}")
            except discord.HTTPException as e: # Log HTTP errors
                logger.error(f"HTTP error deleting {msg_type}: {e}")
            except Exception as e: # Catch any other exceptions
                logger.error(f"Unexpected error cleaning up {msg_type}: {e}")

    def _get_channel(self) -> Optional[discord.TextChannel]:
        """Get the Discord channel if possible"""
        try:
            client = self.client
            if not client:
                return None
            ch = client.get_channel(int(self.channel_id))
            return ch if isinstance(ch, discord.TextChannel) else None
        except Exception:
            return None

    def set_client(self, client: discord.Client) -> None:
        """Attach a Discord client for channel lookups/cleanup."""
        self.client = client

    def current_step(self) -> Optional[str]:
        """
        Get the current step name.

        Returns:
            The current step name or None if all steps are completed
        """
        if self.current_index < len(self.steps):
            return self.steps[self.current_index].name
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
        if self.is_done():
            return []
        return [s.name for s in self.steps[self.current_index:]]

    def add_result(self, step_name: str, value: Any) -> None:
        """ # Add a result for a step.
        Add a result for a step.

        Args:
            step_name: The step name
            value: The result value
        """
        self.results[step_name] = SurveyResult(step_name=step_name, value=value)
        logger.debug(f"Added result for step {step_name} for user {self.user_id}") # Change to DEBUG


class SurveyManager:
    """
    Manages active surveys across channels.
    """
    def __init__(self):
        """Initialize the survey manager."""
        self.surveys: Dict[str, SurveyFlow] = {}  # Use channel_id as key
        self.sessions: Dict[str, SurveyFlow] = {}  # Map session_id -> SurveyFlow

    def create_survey(self, user_id: str, channel_id: str, steps: List[SurveyStep], session_id: str, client: Optional[discord.Client] = None) -> SurveyFlow:
        """Create and track a new survey instance.

        Args:
        user_id: Discord user ID
        channel_id: Discord channel ID
        steps: List of survey step names
        session_id: Combined channel.user ID from initial request
        client: Optional Discord client for message cleanup utilities

        Returns:
            The created SurveyFlow instance

        Raises:
            ValueError: If parameters are invalid
        """
        if not all([user_id, channel_id]) or not isinstance(steps, list):
            raise ValueError("Invalid survey parameters")

        try:
            survey = SurveyFlow(channel_id, steps, user_id, session_id, client=client)
            self.surveys[str(channel_id)] = survey  # Use channel_id as key
            self.sessions[str(session_id)] = survey  # Index by session for O(1) lookup
            logger.info(f"Created new survey for channel {channel_id}") # Log survey creation
            return survey
        except Exception as e:
            logger.error(f"Failed to create survey: {e}")
            raise ValueError("Survey creation failed") from e

    def get_survey(self, channel_id: str) -> Optional[SurveyFlow]:
        """Get survey by channel ID.

        Args:
            channel_id: Discord channel ID to lookup
        """
        # Removed user_id parameter as survey is channel-bound
        key = str(channel_id)
        survey = self.surveys.get(key)
        if survey:
            logger.debug(f"Found survey for channel {key}")
        else:
            logger.debug(f"No active survey for channel {key}")
        return survey

    def get_survey_by_session(self, session_id: str) -> Optional[SurveyFlow]:
        """Get survey by session ID."""
        # O(1) lookup using session index
        survey = self.sessions.get(str(session_id))
        if not survey:
            logger.debug(f"No active survey for session {session_id}")
        return survey

    def record_step_result(self, channel_id: str, step_name: str, value: Any) -> None:
        """Record a step result for a channel-scoped survey without advancing state.

        Args:
            channel_id: Discord channel ID
            step_name: Survey step name
            value: Collected value
        """
        survey = self.get_survey(channel_id)
        if not survey:
            logger.debug(f"record_step_result: no survey for channel {channel_id}; step={step_name}")
            return
        try:
            survey.add_result(step_name, value)
        except Exception as e:
            logger.error(
                f"Failed to record result for channel {channel_id}, step {step_name}, value={value}: {e}",
                exc_info=True,
            )

    def remove_survey(self, channel_id: str) -> None:
        """Remove a survey for a channel.

        Args:
            channel_id: The Discord channel ID
        """
        key = str(channel_id)
        survey = self.surveys.get(key)
        if survey:
            if survey.active_view:
                survey.active_view.stop()
            del self.surveys[key]
            # Remove from session index as well
            try:
                self.sessions.pop(str(survey.session_id), None)
            except Exception:
                logger.warning(f"Failed to remove session index for channel {key}")
            logger.info(f"Removed survey for channel {key}") # Log survey removal
        else:
            logger.warning(f"Attempted to remove survey for channel {key}, but none was found")


# Global survey manager instance
survey_manager = SurveyManager()
