from __future__ import annotations

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


def format_date_ua(date_str: str) -> str:
    """Return a date formatted as ``DD MMMM YY`` in Ukrainian."""
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    return f"{dt.day:02d} {_MONTHS[dt.month - 1]} {dt.year % 100:02d}"


def is_valid_iso_date(date_str: str) -> bool:
    """Return True if ``date_str`` is a valid ``YYYY-MM-DD`` date."""
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
        return True
    except ValueError:
        return False
