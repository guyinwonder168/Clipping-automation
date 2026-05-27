"""Centralized logging configuration for Clipper Agency."""

import logging
import sys
from typing import Any


def setup_logging(level: str = "INFO") -> None:
    """Configure root logger with structured format.

    Called once at application startup. Subsequent calls are no-ops.
    """
    if logging.getLogger().hasHandlers():
        return

    numeric_level = getattr(logging, level.upper(), logging.INFO)

    logging.basicConfig(
        level=numeric_level,
        format="%(asctime)s [%(levelname)-5s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
        stream=sys.stderr,
        force=True,
    )


def get_logger(name: str) -> logging.Logger:
    """Get a logger for a named component.

    Usage::

        logger = get_logger(__name__)
        logger.info("Agent starting")
        logger.error("Pipeline failed: %s", exc_info=True)
    """
    return logging.getLogger(name)
