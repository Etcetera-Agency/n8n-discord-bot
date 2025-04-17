import logging
import sys
from typing import Optional

def setup_logging(level: int = logging.INFO, name: str = 'discord_bot') -> logging.Logger:
    """
    Set up logging with a structured approach.
    
    Args:
        level: The logging level (default: INFO)
        name: The logger name (default: 'discord_bot')
        
    Returns:
        A configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Remove existing handlers if any
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # Console handler
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(level)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console.setFormatter(formatter)
    logger.addHandler(console)
    
    return logger

# Default logger instance
logger = setup_logging(level=logging.DEBUG)

# Add file handler
file_handler = logging.FileHandler('server.log')
file_handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

logger.info("Logger initialized in debug mode with file output")