# ABOUTME: Tests for RecordStore — filtering, sorting, line mode, and count properties.
# ABOUTME: All tests use ParsedLine directly; no file I/O needed.
from datetime import datetime, timezone

import pytest

from tav.loader import KIND_ERROR
from tav.store import RecordStore
from tests.conftest import make_object, make_error, make_primitive


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
# Empty store
# ---------------------------------------------------------------------------


def test_empty_store_len_is_zero():
    store = RecordStore([])
    assert len(store) == 0


def test_empty_store_getitem_raises_index_error():
    store = RecordStore([])
    with pytest.raises(IndexError):
        _ = store[0]


def test_out_of_bounds_access_raises_index_error():
    store = RecordStore([make_object(1, {"v": 1})])
    with pytest.raises(IndexError):
        _ = store[1]


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


def test_sort_by_time_chronological_order():
    """Sorting records produces true chronological order regardless of input format."""
    from tav.time_parse import parse_timestamp

    lines = [
        make_object(1, {"ts": "2024-01-03T00:00:00"}),  # naive ISO
        make_object(2, {"ts": "2024-01-01T00:00:00Z"}),  # aware ISO
        make_object(3, {"ts": 1704153600}),  # epoch (2024-01-02)
        make_object(4, {"ts": "2024-01-04 00:00:00"}),  # strptime
    ]
    store = RecordStore(lines)
    store.sort_by_time("ts", parse_timestamp)
    assert [store[i].line_number for i in range(4)] == [2, 3, 1, 4]


# ---------------------------------------------------------------------------
# field_tree
# ---------------------------------------------------------------------------


def test_field_tree_flat_object():
    lines = [make_object(1, {"a": 1, "b": "hello"})]
    store = RecordStore(lines)
    tree = store.field_tree()
    assert tree == {"a": {}, "b": {}}


def test_field_tree_nested():
    lines = [make_object(1, {"user": {"name": "alice", "age": 30}})]
    store = RecordStore(lines)
    tree = store.field_tree()
    assert tree == {"user": {"name": {}, "age": {}}}


def test_field_tree_merges_across_records():
    lines = [
        make_object(1, {"a": 1, "b": 2}),
        make_object(2, {"b": 3, "c": 4}),
    ]
    store = RecordStore(lines)
    tree = store.field_tree()
    assert tree == {"a": {}, "b": {}, "c": {}}


def test_field_tree_max_depth():
    lines = [make_object(1, {"l1": {"l2": {"l3": {"l4": 42}}}})]
    store = RecordStore(lines)
    tree = store.field_tree(max_depth=2)
    assert tree == {"l1": {"l2": {}}}


def test_field_tree_ignores_non_objects():
    lines = [
        make_object(1, {"a": 1}),
        make_error(2),
        make_primitive(3, 99),
    ]
    store = RecordStore(lines)
    tree = store.field_tree()
    assert tree == {"a": {}}


def test_field_tree_mixed_types():
    """When a field is a dict in one record and a scalar in another, children are preserved."""
    lines = [
        make_object(1, {"x": {"nested": 1}}),
        make_object(2, {"x": "scalar"}),
    ]
    store = RecordStore(lines)
    tree = store.field_tree()
    assert tree == {"x": {"nested": {}}}


def test_field_tree_array_of_objects():
    """Array-of-objects field: child keys from items are merged into the tree."""
    lines = [make_object(1, {"r": [{"x": 1, "y": 2}, {"x": 3, "z": 4}]})]
    store = RecordStore(lines)
    tree = store.field_tree()
    assert tree == {"r": {"x": {}, "y": {}, "z": {}}}


def test_field_tree_nested_array_of_objects():
    """Nested arrays of objects recurse to correct depth."""
    lines = [make_object(1, {"outer": {"items": [{"val": 1}]}})]
    store = RecordStore(lines)
    tree = store.field_tree()
    assert tree == {"outer": {"items": {"val": {}}}}


# ---------------------------------------------------------------------------
# visible_fields
# ---------------------------------------------------------------------------


def test_visible_fields_default_none():
    store = RecordStore([make_object(1, {"a": 1})])
    assert store.visible_fields is None


def test_set_and_get_visible_fields():
    store = RecordStore([make_object(1, {"a": 1, "b": 2})])
    selection = {("a",), ("b",)}
    store.set_visible_fields(selection)
    assert store.visible_fields == selection


def test_set_visible_fields_none_clears():
    store = RecordStore([make_object(1, {"a": 1})])
    store.set_visible_fields({("a",)})
    store.set_visible_fields(None)
    assert store.visible_fields is None
