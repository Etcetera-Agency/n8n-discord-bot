from __future__ import annotations

"""Utilities for formatting and validating dates."""

from datetime import datetime

_MONTHS = [
    "січня",
    "лютого",
    "березня",
    "квітня",
    "травня",
    "червня",
    "липня",
    "серпня",
    "вересня",
    "жовтня",
    "листопада",
    "грудня",
]

_WEEKDAYS = [
    "Понеділок",
    "Вівторок",
    "Середа",
    "Четвер",
    "П'ятниця",
    "Субота",
    "Неділя",
]


def format_date_ua(date_str: str) -> str:
    """Return a date formatted as ``Weekday DD month YYYY`` in Ukrainian."""
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    weekday = _WEEKDAYS[dt.weekday()]
    month = _MONTHS[dt.month - 1]
    return f"{weekday} {dt.day:02d} {month} {dt.year}"


def is_valid_iso_date(date_str: str) -> bool:
    """Return True if ``date_str`` is a valid ``YYYY-MM-DD`` date."""
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
        return True
    except ValueError:
        return False
