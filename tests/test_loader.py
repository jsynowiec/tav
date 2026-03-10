# ABOUTME: Tests for the JSONL loader module
# ABOUTME: Covers all line kinds, blank skipping, BOM stripping, and line numbering.
import io
import json
import pytest

from tav.loader import load_lines, KIND_OBJECT, KIND_PRIMITIVE, KIND_ARRAY, KIND_ERROR
from tests.fixtures import mixed_jsonl_lines


def _sio(text: str) -> io.StringIO:
    return io.StringIO(text)


# ---------------------------------------------------------------------------
# Empty file
# ---------------------------------------------------------------------------

def test_empty_file_returns_no_records():
    result = load_lines(_sio(""))
    assert result.records == []


# ---------------------------------------------------------------------------
# Blank / whitespace-only lines are skipped
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("line", [
    "\n",
    "   \n",
    "\t\n",
    "\n\n\n",
])
def test_blank_lines_are_skipped(line):
    result = load_lines(_sio(line))
    assert result.records == []


# ---------------------------------------------------------------------------
# JSON objects
# ---------------------------------------------------------------------------

def test_json_object_parsed_as_object_kind():
    result = load_lines(_sio('{"a": 1}\n'))
    assert len(result.records) == 1
    rec = result.records[0]
    assert rec.kind == KIND_OBJECT
    assert rec.value == {"a": 1}
    assert rec.line_number == 1
    assert rec.error is None


# ---------------------------------------------------------------------------
# JSON arrays
# ---------------------------------------------------------------------------

def test_json_array_parsed_as_array_kind():
    result = load_lines(_sio('[1, 2, 3]\n'))
    assert len(result.records) == 1
    rec = result.records[0]
    assert rec.kind == KIND_ARRAY
    assert rec.value == [1, 2, 3]
    assert rec.line_number == 1
    assert rec.error is None


# ---------------------------------------------------------------------------
# JSON primitives
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("raw, expected_value", [
    ("42\n", 42),
    ("3.14\n", 3.14),
    ('"hello"\n', "hello"),
    ("true\n", True),
    ("false\n", False),
    ("null\n", None),
])
def test_json_primitive_parsed_as_primitive_kind(raw, expected_value):
    result = load_lines(_sio(raw))
    assert len(result.records) == 1
    rec = result.records[0]
    assert rec.kind == KIND_PRIMITIVE
    assert rec.value == expected_value
    assert rec.error is None


# ---------------------------------------------------------------------------
# Invalid JSON
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("raw", [
    "not valid json {\n",
    "{unclosed\n",
    "{'single': 'quotes'}\n",
])
def test_invalid_json_stored_as_error_kind(raw):
    result = load_lines(_sio(raw))
    assert len(result.records) == 1
    rec = result.records[0]
    assert rec.kind == KIND_ERROR
    assert rec.value == raw.rstrip("\n")
    assert rec.error is not None
    assert len(rec.error) > 0


# ---------------------------------------------------------------------------
# Mixed file — correct kinds and line numbers
# ---------------------------------------------------------------------------

def test_mixed_file_produces_correct_records_and_line_numbers():
    lines = mixed_jsonl_lines()
    # lines = [obj_line, "", obj_line, primitive, array, invalid, "   ", obj_line]
    # line indices (1-based): 1, 2, 3, 4, 5, 6, 7, 8
    # blank lines 2 and 7 are skipped → 6 records
    text = "\n".join(lines) + "\n"
    result = load_lines(_sio(text))

    assert len(result.records) == 6

    r0 = result.records[0]
    assert r0.kind == KIND_OBJECT
    assert r0.line_number == 1

    r1 = result.records[1]
    assert r1.kind == KIND_OBJECT
    assert r1.line_number == 3

    r2 = result.records[2]
    assert r2.kind == KIND_PRIMITIVE
    assert r2.value == 42
    assert r2.line_number == 4

    r3 = result.records[3]
    assert r3.kind == KIND_ARRAY
    assert r3.value == [1, 2, 3]
    assert r3.line_number == 5

    r4 = result.records[4]
    assert r4.kind == KIND_ERROR
    assert r4.line_number == 6

    r5 = result.records[5]
    assert r5.kind == KIND_OBJECT
    assert r5.line_number == 8


# ---------------------------------------------------------------------------
# BOM stripping
# ---------------------------------------------------------------------------

def test_bom_at_start_of_file_is_stripped():
    # \ufeff is the UTF-8 BOM character
    text = "\ufeff" + '{"key": "value"}\n'
    result = load_lines(_sio(text))
    assert len(result.records) == 1
    rec = result.records[0]
    assert rec.kind == KIND_OBJECT
    assert rec.value == {"key": "value"}


# ---------------------------------------------------------------------------
# Line number correctness including gaps from blank lines
# ---------------------------------------------------------------------------

def test_line_numbers_account_for_blank_lines():
    text = "\n".join([
        '{"x": 1}',   # line 1
        "",            # line 2 — blank, skipped
        "",            # line 3 — blank, skipped
        '{"x": 2}',   # line 4
    ]) + "\n"
    result = load_lines(_sio(text))
    assert len(result.records) == 2
    assert result.records[0].line_number == 1
    assert result.records[1].line_number == 4


# ---------------------------------------------------------------------------
# Load from actual file (tmp_path)
# ---------------------------------------------------------------------------

def test_load_from_file(tmp_path):
    data = [{"ts": "2024-01-01T00:00:00Z", "v": i} for i in range(3)]
    p = tmp_path / "data.jsonl"
    p.write_text("\n".join(json.dumps(d) for d in data) + "\n")
    with p.open() as f:
        result = load_lines(f)
    assert len(result.records) == 3
    for i, rec in enumerate(result.records):
        assert rec.kind == KIND_OBJECT
        assert rec.value == data[i]
        assert rec.line_number == i + 1


# ---------------------------------------------------------------------------
# Load from StringIO
# ---------------------------------------------------------------------------

def test_load_from_string_io():
    text = '{"a": 1}\n{"b": 2}\n'
    result = load_lines(io.StringIO(text))
    assert len(result.records) == 2
    assert result.records[0].kind == KIND_OBJECT
    assert result.records[0].value == {"a": 1}
    assert result.records[1].kind == KIND_OBJECT
    assert result.records[1].value == {"b": 2}


# ---------------------------------------------------------------------------
# Windows CRLF line endings
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("line_ending", ["\r\n", "\n"])
def test_crlf_and_lf_line_endings_parsed_correctly(line_ending):
    lines = ['{"x": 1}', '{"x": 2}', '{"x": 3}']
    text = line_ending.join(lines) + line_ending
    result = load_lines(io.StringIO(text, newline=""))
    assert len(result.records) == 3
    for i, rec in enumerate(result.records):
        assert rec.kind == KIND_OBJECT
        assert rec.value == {"x": i + 1}
        assert rec.line_number == i + 1
