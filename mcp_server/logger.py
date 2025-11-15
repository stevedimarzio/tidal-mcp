"""
Logging configuration for MCP server.
Logs are written to stderr to avoid interfering with MCP's stdout communication.
"""

import logging
import sys
from pathlib import Path


# Create a logger that writes to stderr instead of stdout
# This prevents interference with MCP's stdio protocol
def setup_logger(
    name: str = "tidal_mcp_server", level: int = logging.INFO, log_file: Path | None = None
) -> logging.Logger:
    """
    Set up a logger that writes to stderr (and optionally a file).

    Args:
        name: Logger name
        level: Logging level (default: INFO)
        log_file: Optional path to log file. If None, only logs to stderr.

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Remove existing handlers to avoid duplicates
    logger.handlers.clear()

    # Create formatter
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Handler for stderr (doesn't interfere with MCP stdout)
    stderr_handler = logging.StreamHandler(sys.stderr)
    stderr_handler.setLevel(level)
    stderr_handler.setFormatter(formatter)
    logger.addHandler(stderr_handler)

    # Optional file handler
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    # Prevent propagation to root logger
    logger.propagate = False

    return logger


# Create default logger instance
logger = setup_logger()
