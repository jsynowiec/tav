# ABOUTME: Tests for query.py — JMESPath filter and text/regex search over RecordStore.
# ABOUTME: Covers matching, auto-wrap syntax, empty/invalid inputs, and non-object records.
import pytest

from tav.loader import ParsedLine, KIND_OBJECT, KIND_ERROR, KIND_PRIMITIVE
from tav.store import RecordStore
from tav.query import filter_records, search_records


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_store(records: list[dict], with_errors=False):
    lines = [
        ParsedLine(line_number=i + 1, value=r, kind=KIND_OBJECT)
        for i, r in enumerate(records)
    ]
    if with_errors:
        lines.append(
            ParsedLine(
                line_number=len(lines) + 1,
                value="bad json",
                kind=KIND_ERROR,
                error="parse error",
            )
        )
    store = RecordStore(lines)
    # Default mode is objects-only, which is fine for filter_records
    return store


# ---------------------------------------------------------------------------
# filter_records
# ---------------------------------------------------------------------------


def test_filter_matches_simple_field():
    store = _make_store(
        [
            {"sensor_id": "sensor_1", "value": 10},
            {"sensor_id": "sensor_2", "value": 20},
            {"sensor_id": "sensor_1", "value": 30},
        ]
    )
    result = filter_records(store, "sensor_id == 'sensor_1'")
    assert result == [0, 2]


def test_filter_explicit_bracket_syntax():
    store = _make_store(
        [
            {"sensor_id": "sensor_1", "value": 10},
            {"sensor_id": "sensor_2", "value": 20},
            {"sensor_id": "sensor_1", "value": 30},
        ]
    )
    result = filter_records(store, "[?sensor_id == 'sensor_1']")
    assert result == [0, 2]


def test_filter_returns_empty_for_no_match():
    store = _make_store(
        [
            {"sensor_id": "sensor_1"},
            {"sensor_id": "sensor_2"},
        ]
    )
    result = filter_records(store, "sensor_id == 'sensor_99'")
    assert result == []


def test_filter_raises_on_invalid_expression():
    store = _make_store([{"a": 1}])
    with pytest.raises(ValueError):
        filter_records(store, "$.[[[invalid")


def test_filter_raises_on_empty_expression():
    store = _make_store([{"a": 1}])
    with pytest.raises(ValueError):
        filter_records(store, "")


def test_filter_skips_non_object_records():
    # In default (objects-only) mode, only KIND_OBJECT records are visible.
    lines = [
        ParsedLine(line_number=1, value={"sensor_id": "sensor_1"}, kind=KIND_OBJECT),
        ParsedLine(
            line_number=2, value="bad line", kind=KIND_ERROR, error="parse error"
        ),
        ParsedLine(line_number=3, value=42, kind=KIND_PRIMITIVE),
        ParsedLine(line_number=4, value={"sensor_id": "sensor_1"}, kind=KIND_OBJECT),
    ]
    store = RecordStore(lines)  # default mode: objects only
    result = filter_records(store, "sensor_id == 'sensor_1'")
    # Visible records are indices 0 and 1 (the two objects in the object-only view)
    assert result == [0, 1]


def test_filter_nested_path():
    store = _make_store(
        [
            {"metadata": {"source": "alpha"}, "v": 1},
            {"metadata": {"source": "beta"}, "v": 2},
            {"metadata": {"source": "alpha"}, "v": 3},
        ]
    )
    result = filter_records(store, "[?metadata.source == 'alpha']")
    assert result == [0, 2]


def test_filter_numeric_comparison():
    store = _make_store(
        [
            {"value": 10},
            {"value": 20},
            {"value": 30},
        ]
    )
    result = filter_records(store, "value > `15`")
    assert result == [1, 2]


def test_filter_bare_integer_error_suggests_backticks():
    store = _make_store([{"series": 88665234}])
    with pytest.raises(ValueError, match="backtick"):
        filter_records(store, "series == 88665234")


def test_filter_bare_float_error_suggests_backticks():
    store = _make_store([{"value": 3.14}])
    with pytest.raises(ValueError, match="backtick"):
        filter_records(store, "value == 3.14")


def test_filter_bare_true_warns_not_literal():
    store = _make_store([{"active": True}])
    with pytest.raises(ValueError, match="field name") as exc_info:
        filter_records(store, "active == true")
    assert "backtick" in str(exc_info.value)


def test_filter_bare_false_warns_not_literal():
    store = _make_store([{"active": False}])
    with pytest.raises(ValueError):
        filter_records(store, "active == false")


def test_filter_bare_null_warns_not_literal():
    store = _make_store([{"field": None}])
    with pytest.raises(ValueError):
        filter_records(store, "field == null")


def test_filter_backtick_true_works():
    store = _make_store(
        [
            {"active": True},
            {"active": False},
            {"active": "true"},
        ]
    )
    result = filter_records(store, "active == `true`")
    assert result == [0]


def test_filter_backtick_number_equality():
    store = _make_store(
        [
            {"value": 42},
            {"value": 43},
        ]
    )
    result = filter_records(store, "value == `42`")
    assert result == [0]


def test_filter_field_named_true_raises_warning():
    # Field names like "true" are pathological; the warning fires regardless
    store = _make_store([{"true": "yes"}])
    with pytest.raises(ValueError):
        filter_records(store, "true == 'yes'")


# ---------------------------------------------------------------------------
# search_records
# ---------------------------------------------------------------------------


def test_search_finds_text_match():
    store = _make_store(
        [
            {"sensor_id": "sensor_1", "value": 10},
            {"sensor_id": "sensor_2", "value": 20},
            {"sensor_id": "sensor_1", "value": 30},
        ]
    )
    result = search_records(store, "sensor_1")
    assert result == [0, 2]


def test_search_is_case_insensitive():
    store = _make_store(
        [
            {"name": "alice"},
            {"name": "Bob"},
            {"name": "CHARLIE"},
        ]
    )
    result = search_records(store, "ALICE")
    assert result == [0]


def test_search_returns_empty_for_no_match():
    store = _make_store(
        [
            {"sensor_id": "sensor_1"},
            {"sensor_id": "sensor_2"},
        ]
    )
    result = search_records(store, "sensor_99")
    assert result == []


def test_search_raises_on_invalid_regex():
    store = _make_store([{"a": 1}])
    with pytest.raises(ValueError):
        search_records(store, "[unclosed")


def test_search_raises_on_empty_pattern():
    store = _make_store([{"a": 1}])
    with pytest.raises(ValueError):
        search_records(store, "")


def test_search_includes_non_object_records():
    lines = [
        ParsedLine(line_number=1, value={"a": 1}, kind=KIND_OBJECT),
        ParsedLine(
            line_number=2, value="bad json here", kind=KIND_ERROR, error="parse error"
        ),
        ParsedLine(line_number=3, value=42, kind=KIND_PRIMITIVE),
    ]
    store = RecordStore(lines)
    store.toggle_line_mode()
    result = search_records(store, "bad json")
    assert result == [1]


def test_filter_does_not_leak_sentinel_key():
    """After filtering, no record should contain internal sentinel keys."""
    store = _make_store(
        [
            {"sensor_id": "sensor_1", "value": 10},
            {"sensor_id": "sensor_2", "value": 20},
        ]
    )
    filter_records(store, "sensor_id == 'sensor_1'")
    for i in range(len(store)):
        for key in store[i].value:
            assert not key.startswith("__tav_"), f"Sentinel key leaked: {key}"


def test_filter_distinguishes_duplicate_records():
    """Records with identical content should be distinguished by position."""
    store = _make_store(
        [
            {"x": 1},
            {"x": 1},
            {"x": 2},
            {"x": 1},
        ]
    )
    result = filter_records(store, "x == `1`")
    assert result == [0, 1, 3]


def test_search_uses_serialized_json():
    store = _make_store(
        [
            {"timestamp": "2024-01-01T00:00:00Z", "value": 100},
            {"timestamp": "2024-06-15T12:00:00Z", "value": 200},
        ]
    )
    # Search for a pattern that only appears in the JSON serialization
    result = search_records(store, "2024-06-15")
    assert result == [1]
