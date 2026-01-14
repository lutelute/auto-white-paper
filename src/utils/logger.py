"""Logging configuration for Auto White Paper."""

import logging
import sys
from typing import Optional

from rich.console import Console
from rich.logging import RichHandler

console = Console()

_logger: Optional[logging.Logger] = None


def setup_logging(level: str = "info") -> logging.Logger:
    """Setup and configure logging."""
    global _logger

    log_level = getattr(logging, level.upper(), logging.INFO)

    logging.basicConfig(
        level=log_level,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[
            RichHandler(
                console=console,
                rich_tracebacks=True,
                show_time=True,
                show_path=False,
            )
        ],
    )

    _logger = logging.getLogger("awp")
    _logger.setLevel(log_level)

    return _logger


def get_logger() -> logging.Logger:
    """Get the application logger."""
    global _logger
    if _logger is None:
        _logger = setup_logging()
    return _logger
