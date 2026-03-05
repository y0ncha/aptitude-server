"""Logging bootstrap helpers."""

from __future__ import annotations

import logging

LOG_FORMAT = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"


def configure_logging(level: str) -> None:
    """Configure process logging with a deterministic format."""
    resolved_level = getattr(logging, level.upper(), logging.INFO)
    logging.basicConfig(level=resolved_level, format=LOG_FORMAT, force=True)
