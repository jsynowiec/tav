# ABOUTME: Parses timestamp values from various formats into datetime objects.
# ABOUTME: Supports Unix epoch (seconds/ms), ISO 8601, and common strptime formats.
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

_RANGE_MIN = datetime(2000, 1, 1, tzinfo=timezone.utc).timestamp()
_RANGE_MAX = datetime(2040, 12, 31, 23, 59, 59, tzinfo=timezone.utc).timestamp()

_STRPTIME_FORMATS = [
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d %H:%M:%S.%f",
    "%d/%m/%Y %H:%M:%S",
    "%Y-%m-%d",
]


def parse_timestamp(value: Any) -> datetime | None:
    """Parse a value into a datetime, or return None if unrecognised."""
    if isinstance(value, bool):
        return None

    if isinstance(value, (int, float)):
        return _parse_epoch(value)

    if isinstance(value, str):
        return _parse_string(value)

    return None


def _parse_epoch(value: int | float) -> datetime | None:
    seconds = value / 1000.0 if value > 1e12 else float(value)
    if not (_RANGE_MIN <= seconds <= _RANGE_MAX):
        return None
    return datetime.fromtimestamp(seconds, tz=timezone.utc)


def _parse_string(value: str) -> datetime | None:
    # Try fromisoformat first (handles ISO 8601 with/without TZ, Python 3.11+ handles Z)
    try:
        dt = datetime.fromisoformat(value)
        return _normalise_tz(dt)
    except ValueError:
        pass

    # Try strptime fallback formats
    for fmt in _STRPTIME_FORMATS:
        try:
            dt = datetime.strptime(value, fmt)
            return _normalise_tz(dt)
        except ValueError:
            continue

    return None


def _normalise_tz(dt: datetime) -> datetime:
    """Normalize any datetime to UTC: convert tz-aware, assume UTC for naive."""
    if dt.tzinfo is not None:
        return dt.astimezone(timezone.utc)
    return dt.replace(tzinfo=timezone.utc)
