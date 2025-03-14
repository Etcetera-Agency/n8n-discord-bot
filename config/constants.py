import discord
from enum import Enum, auto
from typing import Dict, Any, List

# Workload options
WORKLOAD_OPTIONS = ["Нічого немає", "2", "5", "10", "15", "20", "25", "30", "35", "40", "45", "50"]

# Weekday options for day off selection
WEEKDAY_OPTIONS = [
    discord.SelectOption(label="Monday", value="Monday"),
    discord.SelectOption(label="Tuesday", value="Tuesday"),
    discord.SelectOption(label="Wednesday", value="Wednesday"),
    discord.SelectOption(label="Thursday", value="Thursday"),
    discord.SelectOption(label="Friday", value="Friday"),
    discord.SelectOption(label="Saturday", value="Saturday"),
    discord.SelectOption(label="Sunday", value="Sunday")
]

# Month names
MONTHS = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December"
]

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