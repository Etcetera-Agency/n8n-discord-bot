"""
Adapter interface for PostgreSQL database operations.
"""
from typing import Dict, TypedDict
from datetime import datetime

class Record(TypedDict):
    """Represents a survey step record from the database."""
    completed: bool
    updated: datetime

class PostgresClient:
    """
    An interface for interacting with the survey tracking database.
    This class defines the methods for database operations but does not
    contain any implementation, keeping it abstract.
    """

    def latest_weekly_status(self, session_id: str, week_start: datetime) -> Dict[str, Record]:
        """
        Retrieves the latest status for each survey step within a given week.

        This method should execute a query equivalent to:
        SELECT DISTINCT ON (step_name)
            step_name,
            completed,
            updated
        FROM n8n_survey_steps_missed
        WHERE session_id = :session_id
            AND updated >= :week_start
        ORDER BY step_name, updated DESC;

        Args:
            session_id: The channel or session identifier.
            week_start: The starting datetime of the week (Monday 00:00 Kyiv time).

        Returns:
            A dictionary where keys are step names and values are Record objects
            containing the completion status and update timestamp.
        """
        pass

    def upsert_survey_step(self, session_id: str, step_name: str, completed: bool) -> None:
        """
        Inserts or updates a survey step record.

        This operation should perform an 'upsert' (insert or update).
        The conflict target for the update should be on the (session_id, step_name)
        columns to ensure each step is unique per session.

        Args:
            session_id: The channel or session identifier.
            step_name: The name of the survey step.
            completed: The completion status of the step.
        """
        pass
