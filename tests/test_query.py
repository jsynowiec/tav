# ABOUTME: Tests for query.py — JMESPath filter and text/regex search over RecordStore.
# ABOUTME: Covers matching, auto-wrap syntax, empty/invalid inputs, and non-object records.
import pytest

from tav.loader import ParsedLine, KIND_OBJECT, KIND_ERROR, KIND_PRIMITIVE
from tav.store import RecordStore
from tav.query import filter_records, search_records


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_store(records: list[dict], with_errors=False):
    lines = [ParsedLine(line_number=i+1, value=r, kind=KIND_OBJECT) for i, r in enumerate(records)]
    if with_errors:
        lines.append(ParsedLine(line_number=len(lines)+1, value="bad json", kind=KIND_ERROR, error="parse error"))
    store = RecordStore(lines)
    # Default mode is objects-only, which is fine for filter_records
    return store


# ---------------------------------------------------------------------------
# filter_records
# ---------------------------------------------------------------------------

def test_filter_matches_simple_field():
    store = make_store([
        {"sensor_id": "sensor_1", "value": 10},
        {"sensor_id": "sensor_2", "value": 20},
        {"sensor_id": "sensor_1", "value": 30},
    ])
    result = filter_records(store, "sensor_id == 'sensor_1'")
    assert result == [0, 2]


def test_filter_explicit_bracket_syntax():
    store = make_store([
        {"sensor_id": "sensor_1", "value": 10},
        {"sensor_id": "sensor_2", "value": 20},
        {"sensor_id": "sensor_1", "value": 30},
    ])
    result = filter_records(store, "[?sensor_id == 'sensor_1']")
    assert result == [0, 2]


def test_filter_returns_empty_for_no_match():
    store = make_store([
        {"sensor_id": "sensor_1"},
        {"sensor_id": "sensor_2"},
    ])
    result = filter_records(store, "sensor_id == 'sensor_99'")
    assert result == []


def test_filter_raises_on_invalid_expression():
    store = make_store([{"a": 1}])
    with pytest.raises(ValueError):
        filter_records(store, "$.[[[invalid")


def test_filter_raises_on_empty_expression():
    store = make_store([{"a": 1}])
    with pytest.raises(ValueError):
        filter_records(store, "")


def test_filter_skips_non_object_records():
    # In default (objects-only) mode, only KIND_OBJECT records are visible.
    lines = [
        ParsedLine(line_number=1, value={"sensor_id": "sensor_1"}, kind=KIND_OBJECT),
        ParsedLine(line_number=2, value="bad line", kind=KIND_ERROR, error="parse error"),
        ParsedLine(line_number=3, value=42, kind=KIND_PRIMITIVE),
        ParsedLine(line_number=4, value={"sensor_id": "sensor_1"}, kind=KIND_OBJECT),
    ]
    store = RecordStore(lines)  # default mode: objects only
    result = filter_records(store, "sensor_id == 'sensor_1'")
    # Visible records are indices 0 and 1 (the two objects in the object-only view)
    assert result == [0, 1]


def test_filter_nested_path():
    store = make_store([
        {"metadata": {"source": "alpha"}, "v": 1},
        {"metadata": {"source": "beta"}, "v": 2},
        {"metadata": {"source": "alpha"}, "v": 3},
    ])
    result = filter_records(store, "[?metadata.source == 'alpha']")
    assert result == [0, 2]


def test_filter_numeric_comparison():
    store = make_store([
        {"value": 10},
        {"value": 20},
        {"value": 30},
    ])
    result = filter_records(store, "value > `15`")
    assert result == [1, 2]


# ---------------------------------------------------------------------------
# search_records
# ---------------------------------------------------------------------------

def test_search_finds_text_match():
    store = make_store([
        {"sensor_id": "sensor_1", "value": 10},
        {"sensor_id": "sensor_2", "value": 20},
        {"sensor_id": "sensor_1", "value": 30},
    ])
    result = search_records(store, "sensor_1")
    assert result == [0, 2]


def test_search_is_case_insensitive():
    store = make_store([
        {"name": "alice"},
        {"name": "Bob"},
        {"name": "CHARLIE"},
    ])
    result = search_records(store, "ALICE")
    assert result == [0]


def test_search_returns_empty_for_no_match():
    store = make_store([
        {"sensor_id": "sensor_1"},
        {"sensor_id": "sensor_2"},
    ])
    result = search_records(store, "sensor_99")
    assert result == []


def test_search_raises_on_invalid_regex():
    store = make_store([{"a": 1}])
    with pytest.raises(ValueError):
        search_records(store, "[unclosed")


def test_search_raises_on_empty_pattern():
    store = make_store([{"a": 1}])
    with pytest.raises(ValueError):
        search_records(store, "")


def test_search_includes_non_object_records():
    lines = [
        ParsedLine(line_number=1, value={"a": 1}, kind=KIND_OBJECT),
        ParsedLine(line_number=2, value="bad json here", kind=KIND_ERROR, error="parse error"),
        ParsedLine(line_number=3, value=42, kind=KIND_PRIMITIVE),
    ]
    store = RecordStore(lines)
    store.toggle_line_mode()
    result = search_records(store, "bad json")
    assert result == [1]


def test_search_uses_serialized_json():
    store = make_store([
        {"timestamp": "2024-01-01T00:00:00Z", "value": 100},
        {"timestamp": "2024-06-15T12:00:00Z", "value": 200},
    ])
    # Search for a pattern that only appears in the JSON serialization
    result = search_records(store, "2024-06-15")
    assert result == [1]
