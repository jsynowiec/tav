# ABOUTME: Tests for pure helper functions in the record_list widget.
# ABOUTME: Covers _colorize_value and scroll_to_field offset calculation.
import json
import pytest

from unittest.mock import MagicMock
from rich.segment import Segment

from tests.conftest import make_object
from tav.store import RecordStore
from tav.widgets.record_list import _colorize_value, _is_field_visible, _LINE_NUM_WIDTH, _SEPARATOR, _STYLE_KEY, RecordList


def _text(segments: list[Segment]) -> str:
    """Join segment texts to get the full rendered string."""
    return "".join(s.text for s in segments)


def test_colorize_empty_dict():
    result = _colorize_value({}, max_width=10)
    text = _text(result)
    assert text == "{}" + " " * 8
    assert len(text) == 10


def test_colorize_single_string_value():
    result = _colorize_value({"k": "hello"}, max_width=40)
    text = _text(result)
    assert '{"k":' in text
    assert '"hello"' in text
    assert "}" in text
    assert len(text) == 40


@pytest.mark.parametrize("value, expected_fragment", [
    (True,  "true"),
    (False, "false"),
    (None,  "null"),
    (42,    "42"),
    (3.14,  "3.14"),
])
def test_colorize_value_types(value, expected_fragment):
    result = _colorize_value({"x": value}, max_width=40)
    text = _text(result)
    assert expected_fragment in text
    assert len(text) == 40


def test_colorize_truncates_at_max_width():
    big = {f"key{i}": f"value{i}" for i in range(20)}
    max_width = 30
    result = _colorize_value(big, max_width=max_width)
    text = _text(result)
    assert len(text) == max_width
    assert text.endswith("…")


def test_colorize_pads_to_max_width():
    result = _colorize_value({"a": 1}, max_width=50)
    text = _text(result)
    assert len(text) == 50
    assert text.endswith(" ")


def test_colorize_nested_object():
    """Nested object keys should be colorized, not rendered as a plain json.dumps blob."""
    result = _colorize_value({"a": {"b": 1}}, max_width=40)
    text = _text(result)
    assert '"b":' in text
    key_segs = [s for s in result if '"b":' in s.text]
    assert len(key_segs) == 1
    assert key_segs[0].style == _STYLE_KEY


def test_colorize_nested_array():
    result = _colorize_value({"a": [1, 2]}, max_width=40)
    text = _text(result)
    assert "[" in text
    assert "1" in text
    assert "2" in text


def test_colorize_array_root():
    """A list value should be colorized with brackets and items."""
    result = _colorize_value([1, "x", None], max_width=40)
    text = _text(result)
    assert text.startswith("[")
    assert "1" in text
    assert '"x"' in text
    assert "null" in text


def test_colorize_primitive_string():
    result = _colorize_value("hello", max_width=20)
    text = _text(result)
    assert '"hello"' in text


def test_colorize_primitive_number():
    result = _colorize_value(42, max_width=20)
    text = _text(result)
    assert "42" in text


# ------------------------------------------------------------------
# scroll_to_field
# ------------------------------------------------------------------

def _make_record_list(records):
    """Return a RecordList stub with mocked scroll_to and refresh."""
    rl = object.__new__(RecordList)
    rl._store = RecordStore(records)
    rl._cursor = 0
    rl._sorted = False
    rl.scroll_to = MagicMock()
    rl.refresh = MagicMock()
    return rl


def test_scroll_to_field_computes_correct_offset():
    """scroll_to_field scrolls to prefix_len + field position in rendered content."""
    data = {"foo": "bar", "baz": 42}
    rl = _make_record_list([make_object(1, data)])
    rl.scroll_to_field("foo")
    content = json.dumps(data, separators=(",", ":"))
    pos = content.find('"foo":')
    expected = _LINE_NUM_WIDTH + len(_SEPARATOR) + pos
    rl.scroll_to.assert_called_once_with(x=expected, animate=False)


def test_scroll_to_field_calls_refresh():
    """scroll_to_field calls refresh() after scrolling."""
    rl = _make_record_list([make_object(1, {"alpha": "beta"})])
    rl.scroll_to_field("alpha")
    rl.refresh.assert_called_once()


def test_scroll_to_field_unknown_field_does_not_scroll():
    """scroll_to_field is a no-op when the field is absent from the record."""
    rl = _make_record_list([make_object(1, {"foo": "bar"})])
    rl.scroll_to_field("nonexistent")
    rl.scroll_to.assert_not_called()
    rl.refresh.assert_not_called()


def test_scroll_to_field_empty_store_does_not_scroll():
    """scroll_to_field is a no-op when the store is empty."""
    rl = _make_record_list([])
    rl.scroll_to_field("foo")
    rl.scroll_to.assert_not_called()
    rl.refresh.assert_not_called()


# ------------------------------------------------------------------
# _is_field_visible
# ------------------------------------------------------------------

def test_is_field_visible_exact_match():
    visible = {("a",), ("b",)}
    assert _is_field_visible(("a",), visible) is True


def test_is_field_visible_not_in_set():
    visible = {("a",)}
    assert _is_field_visible(("b",), visible) is False


def test_is_field_visible_descendant_match():
    """Parent path is visible when a descendant is selected."""
    visible = {("user", "name")}
    assert _is_field_visible(("user",), visible) is True


def test_is_field_visible_no_descendant():
    visible = {("user", "name")}
    assert _is_field_visible(("other",), visible) is False


# ------------------------------------------------------------------
# _colorize_value with visible_fields filtering
# ------------------------------------------------------------------

def test_colorize_visible_fields_none_shows_all():
    """visible_fields=None renders everything."""
    result = _colorize_value({"a": 1, "b": 2}, max_width=80, visible_fields=None)
    text = _text(result)
    assert '"a":' in text
    assert '"b":' in text


def test_colorize_visible_fields_hides_unselected():
    """Only selected top-level fields appear in output."""
    result = _colorize_value({"a": 1, "b": 2, "c": 3}, max_width=80, visible_fields={("a",)})
    text = _text(result)
    assert '"a":' in text
    assert '"b":' not in text
    assert '"c":' not in text


def test_colorize_nested_field_filtering():
    """Nested fields are individually filterable."""
    val = {"user": {"name": "alice", "email": "a@b.com"}}
    result = _colorize_value(val, max_width=80, visible_fields={("user", "name")})
    text = _text(result)
    assert '"name":' in text
    assert '"email":' not in text


def test_colorize_parent_shown_when_child_visible():
    """Parent key renders when at least one of its children is selected."""
    val = {"user": {"name": "alice", "age": 30}}
    result = _colorize_value(val, max_width=80, visible_fields={("user", "age")})
    text = _text(result)
    assert '"user":' in text
    assert '"age":' in text
    assert '"name":' not in text


def test_colorize_array_of_objects_with_visible_fields():
    """Array-of-objects: selecting a nested path renders values, not empty objects."""
    val = {"r": [{"x": 1, "y": 2}, {"x": 3, "y": 4}]}
    result = _colorize_value(val, max_width=80, visible_fields={("r", "x")})
    text = _text(result)
    assert '"r":' in text
    assert '"x":' in text
    assert "1" in text
    assert '"y":' not in text
    assert "{}" not in text


def test_colorize_deeply_nested_truncates_at_depth_limit():
    """Nesting beyond depth limit renders ellipsis without crashing."""
    val = {}
    inner = val
    for i in range(25):
        inner[f"l{i}"] = {}
        inner = inner[f"l{i}"]
    inner["leaf"] = 1
    result = _colorize_value(val, max_width=500)
    text = _text(result)
    assert "..." in text
