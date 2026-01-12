"""Logging configuration."""

import logging
import sys

LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
DATE_FORMAT = "%H:%M:%S"

VALID_LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}


def setup_logging(level: str = "INFO") -> None:
    """Configure logging for the application.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR)
    """
    level_upper = level.upper()
    if level_upper not in VALID_LEVELS:
        level_upper = "INFO"
        invalid_level = level
    else:
        invalid_level = None

    numeric_level = getattr(logging, level_upper)

    # Configure root logger at WARNING to suppress third-party noise
    # Use stderr to avoid conflict with interactive menu on stdout
    logging.basicConfig(
        level=logging.WARNING,
        format=LOG_FORMAT,
        datefmt=DATE_FORMAT,
        stream=sys.stderr,
        force=True,
    )

    # Configure application logger at user's level
    app_logger = logging.getLogger("pulse_server")
    app_logger.setLevel(numeric_level)

    # Warn about invalid level after logger is configured
    if invalid_level:
        app_logger.warning("Unknown log level '%s', defaulting to INFO", invalid_level)
