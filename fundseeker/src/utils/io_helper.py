"""Utility helpers for I/O operations."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Optional


def ensure_dir(path: Path) -> Path:
    """Ensure directory exists and return it."""
    path.mkdir(parents=True, exist_ok=True)
    return path


def today_str(date: Optional[datetime] = None) -> str:
    ref = date or datetime.now()
    return ref.strftime("%Y-%m-%d")


def timestamp_str(date: Optional[datetime] = None) -> str:
    ref = date or datetime.now()
    return ref.strftime("%H%M%S")


def ensure_daily_dir(base_dir: Path, date: Optional[str] = None) -> Path:
    """Backward compatibility stub; output now stored directly under base_dir."""
    ensure_dir(base_dir)
    return base_dir


def build_output_path(base_dir: Path, prefix: str, extension: str = ".xlsx", date: Optional[str] = None) -> Path:
    """Generate a timestamped file path under the output directory."""
    ensure_dir(base_dir)
    filename = f"{prefix}_{datetime.now().strftime('%Y%m%d_%H%M%S')}{extension}"
    return base_dir / filename
