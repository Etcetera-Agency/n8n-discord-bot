"""
This module provides pure, stateless utility functions for survey and date
logic. It was intentionally refactored from a class-based model to a
functional approach to separate state management from pure business logic.
"""
from datetime import datetime, timedelta, date
from typing import List, Optional, Dict
import zoneinfo
from clients.postgres import Record # Import Record type

# All timezone-aware operations must use Kyiv time.
TZ_KYIV = zoneinfo.ZoneInfo("Europe/Kyiv")

def week_start_monday_00(now_kyiv: datetime) -> datetime:
    """
    Calculates the start of the current week (Monday 00:00) in Kyiv time.

    Args:
        now_kyiv: A timezone-aware datetime object (in Kyiv timezone).

    Returns:
        A datetime object representing the start of the week.
    """
    if now_kyiv.tzinfo is None:
        raise ValueError("Input datetime must be timezone-aware.")

    start_of_week = now_kyiv - timedelta(days=now_kyiv.weekday())
    return start_of_week.replace(hour=0, minute=0, second=0, microsecond=0)

def is_today(ts: Optional[datetime], now_kyiv: datetime) -> bool:
    """
    Checks if a given timestamp corresponds to today's date in Kyiv time.

    Args:
        ts: The timestamp to check. Can be None.
        now_kyiv: The current time in Kyiv timezone.

    Returns:
        True if the timestamp is on the same day as now_kyiv, False otherwise.
    """
    if ts is None:
        return False

    if now_kyiv.tzinfo is None:
        raise ValueError("now_kyiv must be timezone-aware.")

    # Ensure the timestamp is in Kyiv time for accurate comparison
    ts_kyiv = ts.astimezone(TZ_KYIV)

    return ts_kyiv.date() == now_kyiv.date()

def REQUIRED_STEPS_FOR_WEEK() -> List[str]:
    """
    Returns a list of survey steps that are required for the week.
    This is the central configuration for weekly survey steps.

    Returns:
        A list of step name strings.
    """
    return [
        "workload_today",
        "workload_nextweek",
        "connects_thisweek",
        "day_off_nextweek",
        "day_off_thisweek",
    ]

def get_pending_steps(
    required_steps: List[str],
    weekly_status: Dict[str, Record],
    now_kyiv: datetime
) -> List[str]:
    """
    Determines the list of pending survey steps for the week.

    A step is pending if:
    - It's required but has no completion record for the week.
    - It's marked as not completed.
    - It's a daily recurring task ('workload_today') that was not completed today.
    """
    pending = []
    for step in required_steps:
        record = weekly_status.get(step)

        # The prompt implies Record is a dict, so using .get()
        is_completed = record and record.get('completed', False)

        if not is_completed:
            pending.append(step)
            continue

        # Special handling for daily recurring tasks.
        if step == 'workload_today':
            updated_at = record.get('updated')
            if not is_today(updated_at, now_kyiv):
                pending.append(step)

    return pending
