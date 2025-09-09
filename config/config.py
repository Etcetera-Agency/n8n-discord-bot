import os
from dotenv import load_dotenv
from typing import Optional

load_dotenv()

class Config:
    """Configuration class for the Discord bot application."""
    
    # Discord configuration
    DISCORD_TOKEN: str = os.getenv("DISCORD_TOKEN", "")
    
    # Internal webhook configuration
    WEBHOOK_AUTH_TOKEN: Optional[str] = os.getenv("WEBHOOK_AUTH_TOKEN")

    # Notion configuration
    NOTION_TOKEN: str = os.getenv("NOTION_TOKEN", "")
    NOTION_TEAM_DIRECTORY_DB_ID: str = os.getenv("NOTION_TEAM_DIRECTORY_DB_ID", "")
    NOTION_WORKLOAD_DB_ID: str = os.getenv("NOTION_WORKLOAD_DB_ID", "")
    NOTION_PROFILE_STATS_DB_ID: str = os.getenv("NOTION_PROFILE_STATS_DB_ID", "")

    # Calendar configuration
    GOOGLE_SERVICE_ACCOUNT_B64: str = os.getenv("GOOGLE_SERVICE_ACCOUNT_B64", "")
    CALENDAR_ID: str = os.getenv("CALENDAR_ID", "")

    # Database configuration
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")
    
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

