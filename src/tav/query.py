# ABOUTME: Query functions for filtering and searching records in a RecordStore.
# ABOUTME: Supports JSONPath filter expressions and text/regex pattern search.
import json
import re

from jsonpath_ng.ext import parse as jsonpath_parse

from tav.loader import KIND_OBJECT
from tav.store import RecordStore


def filter_records(store: RecordStore, expression: str) -> list[int]:
    """Return sorted list of store indices where the JSONPath expression matches.

    Only KIND_OBJECT records are evaluated. Raises ValueError for empty or
    invalid expressions.
    """
    if not expression:
        raise ValueError("JSONPath expression must not be empty")

    if not expression.startswith("$"):
        expression = "$" + expression

    try:
        path = jsonpath_parse(expression)
    except Exception as exc:
        raise ValueError(f"Invalid JSONPath expression: {exc}") from exc

    result = []
    for idx in range(len(store)):
        record = store[idx]
        if record.kind != KIND_OBJECT:
            continue
        # Wrap in a list so filter expressions (designed for arrays) work on
        # individual records. A non-empty result means the record matched.
        matches = path.find([record.value])
        if matches:
            result.append(idx)

    return sorted(result)


def search_records(store: RecordStore, pattern: str) -> list[int]:
    """Return sorted list of store indices where the regex pattern matches.

    Searches all records (not just objects). Object records are serialized
    via json.dumps; others via str(). Case-insensitive by default. Raises
    ValueError for invalid regex patterns.
    """
    try:
        compiled = re.compile(pattern, re.IGNORECASE)
    except re.error as exc:
        raise ValueError(str(exc)) from exc

    result = []
    for idx in range(len(store)):
        record = store[idx]
        if record.kind == KIND_OBJECT:
            text = json.dumps(record.value)
        else:
            text = str(record.value)
        if compiled.search(text):
            result.append(idx)

    return sorted(result)
