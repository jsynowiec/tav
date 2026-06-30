# ABOUTME: Parses timestamp values from various formats into datetime objects.
# ABOUTME: Supports Unix epoch (seconds/ms), ISO 8601, and common strptime formats.
from datetime import datetime, timezone, tzinfo as TzInfo
from typing import Any, Callable

# Reasonable timestamp window for log data: 1970 through 2100.
_RANGE_MIN = datetime(1970, 1, 1, tzinfo=timezone.utc).timestamp()
_RANGE_MAX = datetime(2100, 12, 31, 23, 59, 59, tzinfo=timezone.utc).timestamp()

# Values larger than this are treated as milliseconds rather than seconds.
_MS_THRESHOLD = 1e10

_STRPTIME_FORMATS = [
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d %H:%M:%S.%f",
    "%d/%m/%Y %H:%M:%S",
    "%Y-%m-%d",
]


def parse_timestamp(value: Any) -> datetime | None:
    """Parse a value into a datetime, or return None if unrecognised."""
    return create_time_parser()(value)


def _parse_epoch(value: int | float) -> datetime | None:
    seconds = value / 1000.0 if value >= _MS_THRESHOLD else float(value)
    if not (_RANGE_MIN <= seconds <= _RANGE_MAX):
        return None
    return datetime.fromtimestamp(seconds, tz=timezone.utc)


def _parse_string(value: str, assume_tz: TzInfo = timezone.utc) -> datetime | None:
    # Try fromisoformat first (handles ISO 8601 with/without TZ, Python 3.11+ handles Z)
    try:
        dt = datetime.fromisoformat(value)
        return _normalise_tz(dt, assume_tz)
    except ValueError:
        pass

    # Try strptime fallback formats
    for fmt in _STRPTIME_FORMATS:
        try:
            dt = datetime.strptime(value, fmt)
            return _normalise_tz(dt, assume_tz)
        except ValueError:
            continue

    return None


def _normalise_tz(dt: datetime, assume_tz: TzInfo = timezone.utc) -> datetime:
    """Normalize any datetime to UTC: convert tz-aware, stamp naive with assume_tz."""
    if dt.tzinfo is not None:
        return dt.astimezone(timezone.utc)
    return dt.replace(tzinfo=assume_tz).astimezone(timezone.utc)


def create_time_parser(
    assume_tz: TzInfo = timezone.utc,
) -> Callable[[Any], datetime | None]:
    """Return a timestamp parser that interprets naive datetimes in assume_tz."""

    def _parse(value: Any) -> datetime | None:
        if isinstance(value, bool):
            return None
        if isinstance(value, (int, float)):
            return _parse_epoch(value)
        if isinstance(value, str):
            return _parse_string(value, assume_tz)
        return None

    return _parse
