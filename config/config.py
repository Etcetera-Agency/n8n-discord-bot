import os
from dotenv import load_dotenv
from typing import Optional

# Configuration constants
NOTION_TEAM_DIRECTORY_DB_ID = "7113e573923e4c578d788cd94a7bddfa"
NOTION_WORKLOAD_DB_ID = "01e5b4b3d6eb4ad69262008ddc5fa5e4"
NOTION_PROFILE_STATS_DB_ID = "501c314abddb45bfb35d91a217d709d8"

CONNECTS_URL = "https://tech2.etcetera.kiev.ua/set-db-connects"

CALENDAR_ID = "etcetera.kiev.ua_q1bfpjas0rj3e59cv32v05t6bs@group.calendar.google.com"

DB_POSTGRESDB_USER = "postgres"
DB_POSTGRESDB_HOST = "n8n.etcetera.agency"
DB_NAME = "n8n_etc_database"
DB_TABLE = "n8n_survey_steps_missed"

load_dotenv()

class Config:
    """Configuration class for the Discord bot application."""

    # Discord configuration
    DISCORD_TOKEN: str = os.getenv("DISCORD_TOKEN", "")

    # Notion configuration
    NOTION_TOKEN: str = os.getenv("NOTION_TOKEN", "")
    NOTION_TEAM_DIRECTORY_DB_ID: str = NOTION_TEAM_DIRECTORY_DB_ID
    NOTION_WORKLOAD_DB_ID: str = NOTION_WORKLOAD_DB_ID
    NOTION_PROFILE_STATS_DB_ID: str = NOTION_PROFILE_STATS_DB_ID

    # Calendar configuration
    GOOGLE_SERVICE_ACCOUNT_B64: str = os.getenv("GOOGLE_SERVICE_ACCOUNT_B64", "")
    CALENDAR_ID: str = CALENDAR_ID

    # External services
    CONNECTS_URL: str = CONNECTS_URL

    # Database configuration
    DB_POSTGRESDB_PASSWORD: str = os.getenv("DB_POSTGRESDB_PASSWORD", "")
    DB_POSTGRESDB_USER: str = DB_POSTGRESDB_USER
    DB_POSTGRESDB_HOST: str = DB_POSTGRESDB_HOST
    DB_NAME: str = DB_NAME
    DB_TABLE: str = DB_TABLE
    if DB_POSTGRESDB_PASSWORD:
        DATABASE_URL: str = (
            f"postgresql://{DB_POSTGRESDB_USER}:{DB_POSTGRESDB_PASSWORD}@{DB_POSTGRESDB_HOST}/{DB_NAME}"
        )
    else:
        DATABASE_URL: str = ""

    # Session configuration
    SESSION_TTL: int = int(os.getenv("SESSION_TTL", "86400"))  # 24 hours default

    # Web server configuration
    PORT: int = int(os.getenv("PORT", os.getenv("CAPTAIN_PORT", "3000")))
    HOST: str = "0.0.0.0"
    SSL_CERT_PATH: Optional[str] = os.getenv("SSL_CERT_PATH")
    SSL_KEY_PATH: Optional[str] = os.getenv("SSL_KEY_PATH")

    @classmethod
    def validate(cls) -> None:
        """Validate required configuration values."""
        if not cls.DISCORD_TOKEN:
            raise ValueError("DISCORD_TOKEN is required")
        if not cls.NOTION_TOKEN:
            raise ValueError("NOTION_TOKEN is required")
