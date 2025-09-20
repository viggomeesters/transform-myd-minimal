"""
Logging configuration for transform-myd-minimal.

Provides centralized logging setup with appropriate levels and formatting
to replace print statements throughout the application.
"""

import logging
import os
import sys
from typing import Optional


def setup_logging(
    level: Optional[str] = None, format_detailed: bool = False
) -> logging.Logger:
    """
    Set up logging configuration for the application.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
               If None, will use environment variable LOG_LEVEL or default to INFO
        format_detailed: If True, use detailed format with timestamps and module names

    Returns:
        Configured logger instance
    """
    # Get the root logger for the transform_myd_minimal package
    logger = logging.getLogger("transform_myd_minimal")

    # Clear any existing handlers to avoid duplication
    logger.handlers.clear()

    # Determine logging level
    if level is None:
        level = os.getenv("LOG_LEVEL", "INFO")

    # Set the logging level
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    logger.setLevel(numeric_level)

    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(numeric_level)

    # Create formatter
    if format_detailed or os.getenv("LOG_FORMAT", "").lower() == "detailed":
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
    else:
        # Simple format for user-friendly console output
        formatter = logging.Formatter("%(levelname)s: %(message)s")

    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # Prevent propagation to root logger to avoid duplicate messages
    logger.propagate = False

    return logger


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """
    Get a logger instance for a specific module.

    Args:
        name: Module name (usually __name__)

    Returns:
        Logger instance
    """
    if name is None:
        return logging.getLogger("transform_myd_minimal")

    # Ensure the name is under the transform_myd_minimal namespace
    if not name.startswith("transform_myd_minimal"):
        if name.startswith("__main__"):
            name = "transform_myd_minimal.main"
        else:
            name = f'transform_myd_minimal.{name.split(".")[-1]}'

    return logging.getLogger(name)


# Default logger instance for convenience
logger = get_logger()
