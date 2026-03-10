# ABOUTME: Tests for RecordStore — filtering, sorting, line mode, and count properties.
# ABOUTME: All tests use ParsedLine directly; no file I/O needed.
from datetime import datetime, timezone

import pytest

from tav.loader import ParsedLine, KIND_OBJECT, KIND_ERROR, KIND_PRIMITIVE
from tav.store import RecordStore


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_object(line_number, data):
    return ParsedLine(line_number=line_number, value=data, kind=KIND_OBJECT)


def make_error(line_number, raw="bad line"):
    return ParsedLine(line_number=line_number, value=raw, kind=KIND_ERROR, error="parse error")


def make_primitive(line_number, value):
    return ParsedLine(line_number=line_number, value=value, kind=KIND_PRIMITIVE)


def _sample_lines():
    """Return a mixed list: 3 objects, 1 error, 1 primitive."""
    return [
        make_object(1, {"ts": "2024-01-01", "v": 10}),
        make_object(2, {"ts": "2024-01-02", "v": 20}),
        make_error(3),
        make_primitive(4, 42),
        make_object(5, {"ts": "2024-01-03", "v": 30}),
    ]


# ---------------------------------------------------------------------------
# Default mode — objects only
# ---------------------------------------------------------------------------

def test_len_returns_object_count_by_default():
    store = RecordStore(_sample_lines())
    assert len(store) == 3


def test_len_returns_all_after_toggle():
    store = RecordStore(_sample_lines())
    store.toggle_line_mode()
    assert len(store) == 5


def test_toggle_twice_restores_objects_only():
    store = RecordStore(_sample_lines())
    store.toggle_line_mode()
    store.toggle_line_mode()
    assert len(store) == 3


def test_getitem_accesses_visible_records():
    store = RecordStore(_sample_lines())
    # Default mode: only 3 objects
    assert store[0].line_number == 1
    assert store[1].line_number == 2
    assert store[2].line_number == 5


# ---------------------------------------------------------------------------
# Filtering
# ---------------------------------------------------------------------------

def test_apply_filter_narrows_visible_records():
    store = RecordStore(_sample_lines())
    store.apply_filter(lambda rec: rec.value.get("v", 0) > 15)
    assert len(store) == 2
    assert store[0].line_number == 2
    assert store[1].line_number == 5


def test_clear_filter_restores_all_visible():
    store = RecordStore(_sample_lines())
    store.apply_filter(lambda rec: rec.value.get("v", 0) > 15)
    store.clear_filter()
    # Back to default mode (objects only), no filter
    assert len(store) == 3


def test_filter_and_mode_are_independent():
    store = RecordStore(_sample_lines())
    store.toggle_line_mode()  # all-lines mode
    store.apply_filter(lambda rec: rec.kind == KIND_ERROR)
    assert len(store) == 1
    assert store[0].kind == KIND_ERROR


# ---------------------------------------------------------------------------
# all_fields
# ---------------------------------------------------------------------------

def test_all_fields_unions_object_keys():
    lines = [
        make_object(1, {"a": 1, "b": 2}),
        make_object(2, {"b": 3, "c": 4}),
    ]
    store = RecordStore(lines)
    assert store.all_fields() == {"a", "b", "c"}


def test_all_fields_ignores_non_objects():
    lines = [
        make_object(1, {"a": 1}),
        make_error(2),
        make_primitive(3, 99),
    ]
    store = RecordStore(lines)
    assert store.all_fields() == {"a"}


# ---------------------------------------------------------------------------
# Count properties
# ---------------------------------------------------------------------------

def test_total_count_ignores_filter_and_mode():
    store = RecordStore(_sample_lines())
    store.apply_filter(lambda rec: False)  # filter everything out
    assert store.total_count == 5


def test_object_count_correct():
    store = RecordStore(_sample_lines())
    assert store.object_count == 3


def test_error_count_correct():
    store = RecordStore(_sample_lines())
    assert store.error_count == 1


# ---------------------------------------------------------------------------
# Sorting
# ---------------------------------------------------------------------------

def _ts(iso: str) -> datetime:
    return datetime.fromisoformat(iso).replace(tzinfo=timezone.utc)


def _parser(value):
    """Simple parser: value is an ISO date string or None if unparseable."""
    if isinstance(value, str):
        try:
            return _ts(value)
        except ValueError:
            return None
    return None


def test_sort_by_time_orders_records():
    lines = [
        make_object(1, {"ts": "2024-01-03", "v": 30}),
        make_object(2, {"ts": "2024-01-01", "v": 10}),
        make_object(3, {"ts": "2024-01-02", "v": 20}),
    ]
    store = RecordStore(lines)
    store.sort_by_time("ts", _parser)
    assert store[0].line_number == 2  # 2024-01-01
    assert store[1].line_number == 3  # 2024-01-02
    assert store[2].line_number == 1  # 2024-01-03


def test_sort_puts_unparseable_at_end():
    lines = [
        make_object(1, {"ts": "2024-01-02"}),
        make_object(2, {"ts": "not-a-date"}),
        make_object(3, {"ts": "2024-01-01"}),
    ]
    store = RecordStore(lines)
    store.sort_by_time("ts", _parser)
    assert store[0].line_number == 3  # 2024-01-01
    assert store[1].line_number == 1  # 2024-01-02
    assert store[2].line_number == 2  # unparseable — goes to end


def test_reset_sort_restores_file_order():
    lines = [
        make_object(1, {"ts": "2024-01-03"}),
        make_object(2, {"ts": "2024-01-01"}),
        make_object(3, {"ts": "2024-01-02"}),
    ]
    store = RecordStore(lines)
    store.sort_by_time("ts", _parser)
    store.reset_sort()
    assert store[0].line_number == 1
    assert store[1].line_number == 2
    assert store[2].line_number == 3
