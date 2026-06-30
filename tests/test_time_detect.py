# ABOUTME: Tests for time-field auto-detection heuristics in time_detect module.
# ABOUTME: Covers name heuristics, value heuristics, sparse records, and edge cases.
import pytest

from tav.time_detect import detect_time_field


def _ts(i: int) -> str:
    """Build a valid ISO timestamp for test data."""
    return f"2024-01-{i % 28 + 1:02d}T{i % 24:02d}:00:00Z"


# ---------------------------------------------------------------------------
# Name heuristic — common field names
# ---------------------------------------------------------------------------


def test_detects_by_common_name():
    records = [{"timestamp": _ts(i), "val": i} for i in range(10)]
    assert detect_time_field(records) == "timestamp"


@pytest.mark.parametrize(
    "field_name",
    [
        "time",
        "ts",
        "datetime",
        "date",
        "created_at",
        "updated_at",
        "@timestamp",
    ],
)
def test_detects_various_canonical_names(field_name):
    records = [{"val": i, field_name: _ts(i)} for i in range(10)]
    assert detect_time_field(records) == field_name


# ---------------------------------------------------------------------------
# Name heuristic requires parseable value
# ---------------------------------------------------------------------------


def test_name_match_requires_parseable_value():
    # Field named "timestamp" but value is garbage — no name match succeeds.
    # Value heuristic also finds nothing, so result is None.
    records = [{"timestamp": "hello", "sensor": 42} for _ in range(10)]
    assert detect_time_field(records) is None


# ---------------------------------------------------------------------------
# Value heuristic
# ---------------------------------------------------------------------------


def test_value_heuristic_finds_epoch_field():
    # No canonical name; epoch values in a non-canonical field.
    epoch = 1705314600  # 2024-01-15 — within range
    records = [{"sensor_reading": epoch + i, "noise": "foo"} for i in range(10)]
    assert detect_time_field(records) == "sensor_reading"


# ---------------------------------------------------------------------------
# No time field at all
# ---------------------------------------------------------------------------


def test_returns_none_for_no_time_field():
    records = [{"user": "alice", "count": 5, "active": True} for _ in range(10)]
    assert detect_time_field(records) is None


# ---------------------------------------------------------------------------
# Empty input
# ---------------------------------------------------------------------------


def test_empty_records_returns_none():
    assert detect_time_field([]) is None


# ---------------------------------------------------------------------------
# Sample size limits scanning
# ---------------------------------------------------------------------------


def test_sample_size_limits_scanning():
    # First 5 records have a canonical timestamp; records 6-100 have a
    # different field. With sample_size=5 we still detect the first field.
    records = [{"timestamp": _ts(i), "val": i} for i in range(5)]
    records += [{"other_ts": _ts(i), "val": i} for i in range(5, 100)]
    assert detect_time_field(records, sample_size=5) == "timestamp"


# ---------------------------------------------------------------------------
# Name heuristic beats value heuristic
# ---------------------------------------------------------------------------


def test_prefers_name_heuristic_over_value():
    # "ts" matches the name heuristic; "sensor_ts" only matches value heuristic.
    epoch = 1705314600
    records = [{"ts": _ts(i), "sensor_ts": epoch + i} for i in range(10)]
    assert detect_time_field(records) == "ts"


# ---------------------------------------------------------------------------
# Sparse records — missing time field in some rows
# ---------------------------------------------------------------------------


def test_sparse_records_tolerate_missing_field():
    # Half the records are missing the "timestamp" key entirely.
    records = []
    for i in range(10):
        if i % 2 == 0:
            records.append({"timestamp": _ts(i), "val": i})
        else:
            records.append({"val": i})
    assert detect_time_field(records) == "timestamp"


# ---------------------------------------------------------------------------
# Case-insensitive name matching
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "field_name",
    [
        "Timestamp",
        "TIMESTAMP",
        "Time",
        "TIME",
        "TS",
    ],
)
def test_case_insensitive_name_match(field_name):
    records = [{field_name: _ts(i), "val": i} for i in range(10)]
    assert detect_time_field(records) == field_name
