"""Logging helper that writes to hidden date-based directories."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, Tuple

from .io_helper import ensure_daily_dir, today_str

_CACHE: Dict[Tuple[str, str], logging.Logger] = {}


def get_logger(name: str, logs_base: Path, date_str: str | None = None) -> logging.Logger:
    """Return a logger that writes to .fs/logs/<date>/name.log plus console."""
    day = date_str or today_str()
    cache_key = (name, day)
    if cache_key in _CACHE:
        return _CACHE[cache_key]

    log_dir = ensure_daily_dir(logs_base, day)
    log_path = log_dir / f"{name}.log"

    logger = logging.getLogger(f"fundseeker.{name}.{day}")
    logger.setLevel(logging.INFO)
    logger.propagate = False

    # Clear existing handlers tied to this logger before re-adding.
    logger.handlers.clear()

    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter("%(message)s"))

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    _CACHE[cache_key] = logger
    return logger
