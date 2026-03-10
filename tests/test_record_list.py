# ABOUTME: Tests for pure helper functions in the record_list widget.
# ABOUTME: Covers _colorize_value and scroll_to_field offset calculation.
import json
import pytest

from unittest.mock import MagicMock
from rich.segment import Segment

from tests.conftest import make_object
from tav.store import RecordStore
from tav.widgets.record_list import _colorize_value, _LINE_NUM_WIDTH, _SEPARATOR, _STYLE_KEY, RecordList


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
