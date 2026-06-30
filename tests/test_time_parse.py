# ABOUTME: Tests for timestamp parsing logic in time_parse module.
# ABOUTME: Covers epoch ints/floats, ISO 8601 strings, strptime fallbacks, and type guards.
import pytest
from datetime import datetime, timezone

from tav.time_parse import parse_timestamp


# ---------------------------------------------------------------------------
# Epoch seconds (int)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "value, expected",
    [
        (1705314600, datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc)),
        (1000000000, datetime(2001, 9, 9, 1, 46, 40, tzinfo=timezone.utc)),
        (1577836800, datetime(2020, 1, 1, 0, 0, 0, tzinfo=timezone.utc)),
    ],
)
def test_epoch_seconds_returns_utc_datetime(value, expected):
    assert parse_timestamp(value) == expected


# ---------------------------------------------------------------------------
# Epoch milliseconds (int > 1e12)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "value, expected",
    [
        (1705314600000, datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc)),
        (1577836800000, datetime(2020, 1, 1, 0, 0, 0, tzinfo=timezone.utc)),
        # Boundary: exactly 1e12 ms must be treated as ms, not seconds.
        (1_000_000_000_000, datetime(2001, 9, 9, 1, 46, 40, tzinfo=timezone.utc)),
        # Values between 1e10 and 1e12 are ms (unrealistic as seconds).
        (10_000_000_000, datetime(1970, 4, 26, 17, 46, 40, tzinfo=timezone.utc)),
    ],
)
def test_epoch_milliseconds_divides_by_1000(value, expected):
    assert parse_timestamp(value) == expected


# ---------------------------------------------------------------------------
# Epoch float
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "value, expected",
    [
        (1705314600.0, datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc)),
        (1705314600.5, datetime(2024, 1, 15, 10, 30, 0, 500000, tzinfo=timezone.utc)),
        (1705314600000.0, datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc)),
    ],
)
def test_epoch_float_works_correctly(value, expected):
    assert parse_timestamp(value) == expected


# ---------------------------------------------------------------------------
# Epoch out of range → None
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "value",
    [
        -1,  # Negative timestamp
        9999999999999,  # Far future ms — after 2100-12-31
        5_000_000_000,  # Far future seconds — after 2100-12-31
    ],
)
def test_epoch_out_of_range_returns_none(value):
    assert parse_timestamp(value) is None


def test_epoch_unix_epoch_is_accepted():
    """The 1970 lower bound means Unix epoch 0 is now valid."""
    assert parse_timestamp(0) == datetime(1970, 1, 1, 0, 0, 0, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# ISO 8601 strings
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "value, expected",
    [
        (
            "2024-01-15T10:30:00Z",
            datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc),
        ),
        (
            "2024-01-15T10:30:00+05:00",
            datetime(2024, 1, 15, 5, 30, 0, tzinfo=timezone.utc),
        ),
        (
            "2024-01-15T10:30:00.123456Z",
            datetime(2024, 1, 15, 10, 30, 0, 123456, tzinfo=timezone.utc),
        ),
    ],
)
def test_iso8601_with_timezone_returns_utc_datetime(value, expected):
    assert parse_timestamp(value) == expected


@pytest.mark.parametrize(
    "value, expected",
    [
        (
            "2024-01-15T10:30:00",
            datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc),
        ),
        (
            "2024-01-15",
            datetime(2024, 1, 15, 0, 0, 0, tzinfo=timezone.utc),
        ),
    ],
)
def test_iso8601_without_timezone_returns_utc_datetime(value, expected):
    result = parse_timestamp(value)
    assert result == expected
    assert result.tzinfo == timezone.utc


# ---------------------------------------------------------------------------
# strptime fallback formats
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "value, expected",
    [
        (
            "2024-01-15 10:30:00",
            datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc),
        ),
        (
            "2024-01-15 10:30:00.123456",
            datetime(2024, 1, 15, 10, 30, 0, 123456, tzinfo=timezone.utc),
        ),
        (
            "15/01/2024 10:30:00",
            datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc),
        ),
    ],
)
def test_strptime_fallback_formats_parsed_correctly(value, expected):
    result = parse_timestamp(value)
    assert result == expected
    assert result.tzinfo == timezone.utc


# ---------------------------------------------------------------------------
# Invalid strings → None
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "value",
    [
        "not-a-date",
        "2024-13-45",
        "hello world",
        "",
        "2024/01/15",  # unsupported format
    ],
)
def test_invalid_string_returns_none(value):
    assert parse_timestamp(value) is None


# ---------------------------------------------------------------------------
# Non-string/non-numeric types → None
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "value",
    [
        None,
        True,
        False,
        {},
        [],
        {"ts": "2024-01-15"},
        [1705315800],
    ],
)
def test_non_parseable_types_return_none(value):
    assert parse_timestamp(value) is None


# ---------------------------------------------------------------------------
# TZ normalization: any tz-aware input → UTC
# ---------------------------------------------------------------------------


def test_tz_aware_string_normalized_to_utc():
    result = parse_timestamp("2024-01-15T10:30:00+05:00")
    assert result is not None
    assert result.tzinfo == timezone.utc
    assert result == datetime(2024, 1, 15, 5, 30, 0, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# Naive preserved: naive input → tzinfo is None
# ---------------------------------------------------------------------------


def test_naive_string_normalized_to_utc():
    result = parse_timestamp("2024-01-15T10:30:00")
    assert result is not None
    assert result.tzinfo == timezone.utc


# ---------------------------------------------------------------------------
# All parseable inputs → UTC-aware or None
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "value",
    [
        1705314600,  # epoch seconds
        1705314600000,  # epoch milliseconds
        1705314600.5,  # epoch float
        "2024-01-15T10:30:00Z",  # ISO with Z
        "2024-01-15T10:30:00+05:00",  # ISO with offset
        "2024-01-15T10:30:00",  # ISO without tz
        "2024-01-15",  # ISO date only
        "2024-01-15 10:30:00",  # strptime format
        "15/01/2024 10:30:00",  # strptime dd/mm/yyyy
    ],
)
def test_parse_timestamp_always_returns_utc_aware_or_none(value):
    result = parse_timestamp(value)
    assert result is not None
    assert result.tzinfo == timezone.utc


# ---------------------------------------------------------------------------
# create_time_parser with custom timezone
# ---------------------------------------------------------------------------


def test_create_time_parser_with_non_utc_timezone():
    """Naive timestamps interpreted in the given timezone and converted to UTC."""
    from zoneinfo import ZoneInfo
    from tav.time_parse import create_time_parser

    parser = create_time_parser(assume_tz=ZoneInfo("Europe/Warsaw"))
    # 2024-01-15 10:30:00 in Warsaw = 2024-01-15 09:30:00 UTC (CET = UTC+1)
    result = parser("2024-01-15T10:30:00")
    assert result == datetime(2024, 1, 15, 9, 30, 0, tzinfo=timezone.utc)


def test_create_time_parser_aware_input_ignores_assume_tz():
    """Tz-aware inputs are converted to UTC regardless of assume_tz."""
    from zoneinfo import ZoneInfo
    from tav.time_parse import create_time_parser

    parser = create_time_parser(assume_tz=ZoneInfo("US/Eastern"))
    result = parser("2024-01-15T10:30:00+05:00")
    assert result == datetime(2024, 1, 15, 5, 30, 0, tzinfo=timezone.utc)


def test_create_time_parser_default_is_utc():
    """Default factory behaves identically to parse_timestamp."""
    from tav.time_parse import create_time_parser

    parser = create_time_parser()
    result = parser("2024-01-15T10:30:00")
    assert result == parse_timestamp("2024-01-15T10:30:00")
