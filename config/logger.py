import logging
import sys
from pathlib import Path

_initialized = False

# Expose a module-level logger that callers can import.
# It will be configured by setup_logging() once at process start.
logger = logging.getLogger('discord_bot')


def setup_logging(level: int = logging.INFO, name: str = 'discord_bot') -> logging.Logger:
    """
    Initialize structured logging once for the application.

    Idempotent: subsequent calls return the same configured logger
    without re-attaching duplicate handlers.
    """
    global _initialized
    log = logging.getLogger(name)
    if _initialized and log.handlers:
        return log

    log.setLevel(level)

    # Remove existing handlers to avoid duplicates across runs
    for handler in list(log.handlers):
        log.removeHandler(handler)

    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # Console handler
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(level)
    console.setFormatter(formatter)
    log.addHandler(console)

    # File handler (best-effort)
    try:
        logs_dir = Path(__file__).parent.parent / 'logs'
        logs_dir.mkdir(exist_ok=True)
        file_handler = logging.FileHandler(str(logs_dir / 'server.log'))
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        log.addHandler(file_handler)
    except Exception as e:  # pragma: no cover - filesystem issues
        # Use console logger to report file handler setup failure
        log.error(f"Failed to create log file handler: {e}")

    _initialized = True
    return log
