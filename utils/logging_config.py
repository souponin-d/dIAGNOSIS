"""Logging configuration helpers."""

from __future__ import annotations

import logging
from logging import Logger


def setup_logging(level: str = "INFO") -> Logger:
    """Configure and return the root logger.

    Parameters
    ----------
    level:
        The logging level name to apply to the root logger.
    """

    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    return logging.getLogger()
