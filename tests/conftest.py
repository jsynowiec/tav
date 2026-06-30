# ABOUTME: pytest configuration and shared fixtures for tav tests
# ABOUTME: Provides reusable fixtures for JSONL data, temp files, and record stores.
from tav.loader import ParsedLine, KIND_OBJECT, KIND_ERROR, KIND_PRIMITIVE


def make_object(line_number, data):
    return ParsedLine(line_number=line_number, value=data, kind=KIND_OBJECT)


def make_error(line_number, raw="bad line"):
    return ParsedLine(
        line_number=line_number, value=raw, kind=KIND_ERROR, error="parse error"
    )


def make_primitive(line_number, value):
    return ParsedLine(line_number=line_number, value=value, kind=KIND_PRIMITIVE)
