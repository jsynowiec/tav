# ABOUTME: Tests for pure helper functions in the record_list widget.
# ABOUTME: Covers _colorize_value: content, value types, truncation, and recursive structures.
import pytest

from rich.segment import Segment

from tav.widgets.record_list import _colorize_value, _STYLE_KEY


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
