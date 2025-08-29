"""
Adapter interface for Google Calendar API operations.
"""
from datetime import date

class GCalClient:
    """An interface for interacting with the Google Calendar API."""

    def add_day_off_event(self, user_email: str, day_off: date, event_title: str) -> None:
        """
        Creates an all-day event in the user's Google Calendar for a single day.
        """
        pass

    def add_vacation_event(self, user_email: str, start_date: date, end_date: date, event_title: str) -> None:
        """
        Creates an all-day event in the user's Google Calendar for a date range.
        """
        pass
