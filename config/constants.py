import discord # type: ignore
import datetime
import pytz
from enum import Enum, auto
from typing import Dict, Any, List

# Workload options
WORKLOAD_OPTIONS = ["Нічого немає", "2", "5", "10", "15", "20", "25", "30", "35", "40", "45", "50"]

# Weekday options for day off selection
WEEKDAY_OPTIONS = [
    discord.SelectOption(label="Понеділок", value="Понеділок"),
    discord.SelectOption(label="Вівторок", value="Вівторок"),
    discord.SelectOption(label="Середа", value="Середа"),
    discord.SelectOption(label="Четвер", value="Четвер"),
    discord.SelectOption(label="П'ятниця", value="П'ятниця"),
    discord.SelectOption(label="Субота", value="Субота"),
    discord.SelectOption(label="Неділя", value="Неділя")
]

# Month names in Ukrainian
MONTHS = [
    "Січень", "Лютий", "Березень", "Квітень", "Травень", "Червень",
    "Липень", "Серпень", "Вересень", "Жовтень", "Листопад", "Грудень"
]
# Weekday map for day off selection
WEEKDAY_MAP = {
    "Понеділок": 0, "Вівторок": 1, "Середа": 2, "Четвер": 3,
    "П'ятниця": 4, "Субота": 5, "Неділя": 6
}

# View types enum
class ViewType(Enum):
    """Enum for different view types."""
    DYNAMIC = auto()
    SLASH = auto()

# View configurations
VIEW_CONFIGS: Dict[ViewType, Dict[str, Any]] = {
    ViewType.DYNAMIC: {"timeout": 900, "has_survey": True},
    ViewType.SLASH: {"timeout": None, "has_survey": False}
}

# Timezone constants
KYIV_TIMEZONE = pytz.timezone('Europe/Kiev')  # Uses EEST (UTC+3) with DST

# Required survey steps in exact order
SURVEY_FLOW = ["workload_today", "workload_nextweek", "connects_thisweek","day_off_nextweek"]
