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
