# ABOUTME: Tests for pure stats computation functions in stats.py.
# ABOUTME: Covers TimeStats, FieldStats, and DataStats derived from RecordStore.
from datetime import datetime, timezone

import pytest

from tav.loader import ParsedLine, KIND_OBJECT, KIND_ERROR, KIND_PRIMITIVE
from tav.store import RecordStore
from tav.stats import compute_stats, DataStats, TimeStats, FieldStats


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_object(line_number, data):
    return ParsedLine(line_number=line_number, value=data, kind=KIND_OBJECT)


def make_error(line_number, raw="bad line"):
    return ParsedLine(line_number=line_number, value=raw, kind=KIND_ERROR, error="parse error")


def make_primitive(line_number, value):
    return ParsedLine(line_number=line_number, value=value, kind=KIND_PRIMITIVE)


def _no_op_parser(value):
    return None


def _iso_parser(value):
    """Parse an ISO 8601 string into a datetime; return None for anything else."""
    if not isinstance(value, str):
        return None
    try:
        dt = datetime.fromisoformat(value)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# 1. empty store
# ---------------------------------------------------------------------------

def test_compute_stats_empty_store():
    store = RecordStore([])
    result = compute_stats(store, time_field=None, time_parser=_no_op_parser)
    assert isinstance(result, DataStats)
    assert result.total_count == 0
    assert result.filtered_count == 0
    assert result.object_count == 0
    assert result.error_count == 0
    assert result.time_stats is None
    assert result.field_stats == []


# ---------------------------------------------------------------------------
# 2. total vs filtered count
# ---------------------------------------------------------------------------

def test_total_vs_filtered_count():
    lines = [
        make_object(1, {"v": 1}),
        make_object(2, {"v": 2}),
        make_object(3, {"v": 3}),
        make_error(4),
        make_primitive(5, 99),
    ]
    store = RecordStore(lines)
    store.apply_filter(lambda rec: rec.value.get("v", 0) > 1)
    result = compute_stats(store, time_field=None, time_parser=_no_op_parser)
    assert result.total_count == 5
    assert result.filtered_count == 2


# ---------------------------------------------------------------------------
# 3. time_stats None when no time_field
# ---------------------------------------------------------------------------

def test_time_stats_none_when_no_time_field():
    lines = [
        make_object(1, {"ts": "2024-01-01T00:00:00Z", "v": 1}),
        make_object(2, {"ts": "2024-01-02T00:00:00Z", "v": 2}),
    ]
    store = RecordStore(lines)
    result = compute_stats(store, time_field=None, time_parser=_iso_parser)
    assert result.time_stats is None


# ---------------------------------------------------------------------------
# 4. time_stats with valid timestamps
# ---------------------------------------------------------------------------

def test_time_stats_with_valid_timestamps():
    lines = [
        make_object(1, {"ts": "2024-01-01T00:00:00+00:00", "v": 1}),
        make_object(2, {"ts": "2024-01-03T00:00:00+00:00", "v": 2}),
        make_object(3, {"ts": "2024-01-02T00:00:00+00:00", "v": 3}),
    ]
    store = RecordStore(lines)
    result = compute_stats(store, time_field="ts", time_parser=_iso_parser)
    ts = result.time_stats
    assert ts is not None
    assert ts.record_count == 3
    assert ts.min_time == datetime(2024, 1, 1, tzinfo=timezone.utc)
    assert ts.max_time == datetime(2024, 1, 3, tzinfo=timezone.utc)
    assert ts.span_seconds == 2 * 86400.0


# ---------------------------------------------------------------------------
# 5. span_seconds None with only one parseable record
# ---------------------------------------------------------------------------

def test_time_stats_span_none_with_one_record():
    lines = [
        make_object(1, {"ts": "2024-01-01T00:00:00+00:00", "v": 1}),
    ]
    store = RecordStore(lines)
    result = compute_stats(store, time_field="ts", time_parser=_iso_parser)
    ts = result.time_stats
    assert ts is not None
    assert ts.span_seconds is None


# ---------------------------------------------------------------------------
# 6. time_stats skips unparseable values
# ---------------------------------------------------------------------------

def test_time_stats_skips_unparseable():
    lines = [
        make_object(1, {"ts": "not-a-date", "v": 1}),
        make_object(2, {"ts": "2024-01-01T00:00:00+00:00", "v": 2}),
        make_object(3, {"ts": "2024-06-01T00:00:00+00:00", "v": 3}),
        make_object(4, {"ts": "also-bad", "v": 4}),
    ]
    store = RecordStore(lines)
    result = compute_stats(store, time_field="ts", time_parser=_iso_parser)
    ts = result.time_stats
    assert ts is not None
    assert ts.min_time == datetime(2024, 1, 1, tzinfo=timezone.utc)
    assert ts.max_time == datetime(2024, 6, 1, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# 7. field completeness
# ---------------------------------------------------------------------------

def test_field_completeness():
    lines = [
        make_object(1, {"a": 1, "b": 10}),
        make_object(2, {"a": 2}),
        make_object(3, {"a": 3, "b": 30}),
        make_object(4, {"a": 4}),
        make_object(5, {"a": 5, "b": 50}),
    ]
    store = RecordStore(lines)
    result = compute_stats(store, time_field=None, time_parser=_no_op_parser)
    by_name = {fs.name: fs for fs in result.field_stats}
    assert by_name["a"].completeness == 1.0
    assert by_name["b"].present_count == 3
    assert by_name["b"].total_count == 5
    assert by_name["b"].completeness == pytest.approx(0.6)


# ---------------------------------------------------------------------------
# 8. field cardinality low
# ---------------------------------------------------------------------------

def test_field_cardinality_low():
    lines = [make_object(i + 1, {"color": c}) for i, c in enumerate(["red", "green", "blue", "red", "green"])]
    store = RecordStore(lines)
    result = compute_stats(store, time_field=None, time_parser=_no_op_parser)
    fs = result.field_stats[0]
    assert fs.cardinality == "low"
    assert fs.unique_count == 3
    assert fs.value_counts is not None
    assert fs.value_counts['"red"'] == 2
    assert fs.value_counts['"green"'] == 2
    assert fs.value_counts['"blue"'] == 1


# ---------------------------------------------------------------------------
# 9. field cardinality high
# ---------------------------------------------------------------------------

def test_field_cardinality_high():
    lines = [make_object(i + 1, {"id": i}) for i in range(150)]
    store = RecordStore(lines)
    result = compute_stats(store, time_field=None, time_parser=_no_op_parser)
    fs = result.field_stats[0]
    assert fs.cardinality == "high"
    assert fs.unique_count == 150
    assert fs.value_counts is None


# ---------------------------------------------------------------------------
# 10. field value_type numeric
# ---------------------------------------------------------------------------

def test_field_value_type_numeric():
    lines = [make_object(i + 1, {"val": float(i)}) for i in range(5)]
    store = RecordStore(lines)
    result = compute_stats(store, time_field=None, time_parser=_no_op_parser)
    fs = result.field_stats[0]
    assert fs.value_type == "numeric"


# ---------------------------------------------------------------------------
# 11. field value_type mixed
# ---------------------------------------------------------------------------

def test_field_value_type_mixed():
    lines = [
        make_object(1, {"x": 1}),
        make_object(2, {"x": "hello"}),
        make_object(3, {"x": 3}),
    ]
    store = RecordStore(lines)
    result = compute_stats(store, time_field=None, time_parser=_no_op_parser)
    fs = result.field_stats[0]
    assert fs.value_type == "mixed"


# ---------------------------------------------------------------------------
# 12. all fields included
# ---------------------------------------------------------------------------

def test_all_fields_included():
    lines = [
        make_object(1, {"a": 1, "b": 2}),
        make_object(2, {"b": 3, "c": 4}),
        make_object(3, {"a": 5, "d": 6}),
    ]
    store = RecordStore(lines)
    result = compute_stats(store, time_field=None, time_parser=_no_op_parser)
    names = {fs.name for fs in result.field_stats}
    assert names == {"a", "b", "c", "d"}


# ---------------------------------------------------------------------------
# 13. error count in DataStats
# ---------------------------------------------------------------------------

def test_error_count_in_data_stats():
    lines = [
        make_object(1, {"v": 1}),
        make_error(2),
        make_error(3),
        make_primitive(4, 42),
    ]
    store = RecordStore(lines)
    result = compute_stats(store, time_field=None, time_parser=_no_op_parser)
    assert result.error_count == 2
    assert result.object_count == 1
