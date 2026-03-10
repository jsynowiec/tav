# ABOUTME: Tests for pure helper functions in the record_list widget.
# ABOUTME: Covers _colorize_object: content, value types, and truncation.
import pytest

from rich.segment import Segment

from tav.widgets.record_list import _colorize_object


def _text(segments: list[Segment]) -> str:
    """Join segment texts to get the full rendered string."""
    return "".join(s.text for s in segments)


def test_colorize_object_empty_dict():
    result = _colorize_object({}, max_width=10)
    text = _text(result)
    assert text == "{}" + " " * 8
    assert len(text) == 10


def test_colorize_object_single_string_value():
    result = _colorize_object({"k": "hello"}, max_width=40)
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
def test_colorize_object_value_types(value, expected_fragment):
    result = _colorize_object({"x": value}, max_width=40)
    text = _text(result)
    assert expected_fragment in text
    assert len(text) == 40


def test_colorize_object_truncates_at_max_width():
    big = {f"key{i}": f"value{i}" for i in range(20)}
    max_width = 30
    result = _colorize_object(big, max_width=max_width)
    text = _text(result)
    assert len(text) == max_width
    assert text.endswith("…")


def test_colorize_object_pads_to_max_width():
    result = _colorize_object({"a": 1}, max_width=50)
    text = _text(result)
    assert len(text) == 50
    assert text.endswith(" ")
