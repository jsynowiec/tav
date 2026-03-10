# ABOUTME: Tests for query.py — JSONPath filter and text/regex search over RecordStore.
# ABOUTME: Covers matching, auto-prefix, empty/invalid inputs, and non-object records.
import pytest

from tav.loader import ParsedLine, KIND_OBJECT, KIND_ERROR, KIND_PRIMITIVE
from tav.store import RecordStore
from tav.query import filter_records, search_records


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_store_objects(data_list):
    """Build a store from a list of dicts (all KIND_OBJECT). Default mode: objects only."""
    lines = [
        ParsedLine(line_number=i + 1, value=d, kind=KIND_OBJECT)
        for i, d in enumerate(data_list)
    ]
    return RecordStore(lines)


def make_store_mixed(parsed_lines):
    """Build a store from explicit ParsedLine list. Switches to all-lines mode."""
    store = RecordStore(parsed_lines)
    store.toggle_line_mode()
    return store


# ---------------------------------------------------------------------------
# filter_records
# ---------------------------------------------------------------------------

def test_filter_matches_simple_field():
    store = make_store_objects([
        {"sensor_id": "sensor_1", "value": 10},
        {"sensor_id": "sensor_2", "value": 20},
        {"sensor_id": "sensor_1", "value": 30},
    ])
    # jsonpath_ng ext filter syntax: $[?(@.field == value)]
    result = filter_records(store, "$[?(@.sensor_id == sensor_1)]")
    assert result == [0, 2]


def test_filter_auto_prefixes_dollar_dot():
    store = make_store_objects([
        {"sensor_id": "sensor_1", "value": 10},
        {"sensor_id": "sensor_2", "value": 20},
        {"sensor_id": "sensor_1", "value": 30},
    ])
    # Without $. prefix — should auto-prefix to $[?(@.sensor_id == sensor_1)]
    result = filter_records(store, "[?(@.sensor_id == sensor_1)]")
    assert result == [0, 2]


def test_filter_returns_empty_for_no_match():
    store = make_store_objects([
        {"sensor_id": "sensor_1"},
        {"sensor_id": "sensor_2"},
    ])
    result = filter_records(store, "$[?(@.sensor_id == sensor_99)]")
    assert result == []


def test_filter_raises_on_invalid_expression():
    store = make_store_objects([{"a": 1}])
    with pytest.raises(ValueError):
        filter_records(store, "$.[[[invalid")


def test_filter_raises_on_empty_expression():
    store = make_store_objects([{"a": 1}])
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
    result = filter_records(store, "$[?(@.sensor_id == sensor_1)]")
    # Visible records are indices 0 and 1 (the two objects in the object-only view)
    assert result == [0, 1]


def test_filter_nested_path():
    store = make_store_objects([
        {"metadata": {"source": "alpha"}, "v": 1},
        {"metadata": {"source": "beta"}, "v": 2},
        {"metadata": {"source": "alpha"}, "v": 3},
    ])
    result = filter_records(store, "$[?(@.metadata.source == alpha)]")
    assert result == [0, 2]


# ---------------------------------------------------------------------------
# search_records
# ---------------------------------------------------------------------------

def test_search_finds_text_match():
    store = make_store_objects([
        {"sensor_id": "sensor_1", "value": 10},
        {"sensor_id": "sensor_2", "value": 20},
        {"sensor_id": "sensor_1", "value": 30},
    ])
    result = search_records(store, "sensor_1")
    assert result == [0, 2]


def test_search_is_case_insensitive():
    store = make_store_objects([
        {"name": "alice"},
        {"name": "Bob"},
        {"name": "CHARLIE"},
    ])
    result = search_records(store, "ALICE")
    assert result == [0]


def test_search_returns_empty_for_no_match():
    store = make_store_objects([
        {"sensor_id": "sensor_1"},
        {"sensor_id": "sensor_2"},
    ])
    result = search_records(store, "sensor_99")
    assert result == []


def test_search_raises_on_invalid_regex():
    store = make_store_objects([{"a": 1}])
    with pytest.raises(ValueError):
        search_records(store, "[unclosed")


def test_search_includes_non_object_records():
    lines = [
        ParsedLine(line_number=1, value={"a": 1}, kind=KIND_OBJECT),
        ParsedLine(line_number=2, value="bad json here", kind=KIND_ERROR, error="parse error"),
        ParsedLine(line_number=3, value=42, kind=KIND_PRIMITIVE),
    ]
    store = make_store_mixed(lines)
    result = search_records(store, "bad json")
    assert result == [1]


def test_search_uses_serialized_json():
    store = make_store_objects([
        {"timestamp": "2024-01-01T00:00:00Z", "value": 100},
        {"timestamp": "2024-06-15T12:00:00Z", "value": 200},
    ])
    # Search for a pattern that only appears in the JSON serialization
    result = search_records(store, "2024-06-15")
    assert result == [1]
