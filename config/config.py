import os
from dotenv import load_dotenv
from typing import Optional

load_dotenv()

class Config:
    """Configuration class for the Discord bot application."""
    
    # Discord configuration
    DISCORD_TOKEN: str = os.getenv("DISCORD_TOKEN", "")
    
    # N8N webhook configuration
    N8N_WEBHOOK_URL: str = os.getenv("N8N_WEBHOOK_URL", "")
    WEBHOOK_AUTH_TOKEN: Optional[str] = os.getenv("WEBHOOK_AUTH_TOKEN")
    
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
        if not cls.N8N_WEBHOOK_URL:
            raise ValueError("N8N_WEBHOOK_URL is required") 