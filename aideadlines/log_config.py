"""Centralised Loguru configuration.

Provides a pre‑configured ``logger`` instance with a concise, readable format.
All modules should import ``logger`` from this file and use ``logger.info``,
``logger.debug`` etc. instead of ``print``.
"""

import sys
from loguru import logger

_ERROR_FILE = "error.log"

# Remove the default logger to avoid duplicate output
logger.remove()

# Define a consistent format: timestamp | level | message
logger.add(
    sys.stderr,
    # format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level}</level> | <level>{message}</level>",
    level="INFO",
    colorize=True,
    enqueue=True,
)

logger.add(
    _ERROR_FILE,
    level="ERROR",
    colorize=False,
    enqueue=True,
)
