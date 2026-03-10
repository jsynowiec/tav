# ABOUTME: JSONPath-style record filtering and text/regex search for tav
# ABOUTME: Uses jmespath for filter expressions; supports quoted string comparisons.
import json
import re
from typing import TYPE_CHECKING

import jmespath
import jmespath.exceptions

if TYPE_CHECKING:
    from tav.store import RecordStore

from tav.loader import KIND_OBJECT


def filter_records(store: "RecordStore", expression: str) -> list[int]:
    """
    Filter visible records using a JMESPath expression.

    Expression is applied to the list of all visible object records.
    Use filter projection syntax: [?field == 'value']
    Bare expressions without leading '[?' are auto-wrapped: field == 'value' -> [?field == 'value']

    Returns a sorted list of store indices (positions in current store view).
    Raises ValueError for invalid expressions.
    """
    if not expression or not expression.strip():
        raise ValueError("Expression must not be empty")

    expr = expression.strip()
    if not expr.startswith("[?"):
        expr = f"[?{expr}]"

    try:
        compiled = jmespath.compile(expr)
    except jmespath.exceptions.ParseError as e:
        raise ValueError(f"Invalid expression: {e}") from e

    # Collect (store_index, value) for all visible object records
    indexed_values: list[tuple[int, dict]] = []
    for i in range(len(store)):
        record = store[i]
        if record.kind == KIND_OBJECT:
            indexed_values.append((i, record.value))

    if not indexed_values:
        return []

    values = [v for _, v in indexed_values]

    try:
        matched = compiled.search(values) or []
    except jmespath.exceptions.JMESPathError as e:
        raise ValueError(str(e)) from e

    # jmespath returns references to the same dict objects from the input list
    matched_ids = {id(v) for v in matched}
    return [idx for idx, val in indexed_values if id(val) in matched_ids]


def search_records(store: "RecordStore", pattern: str) -> list[int]:
    """
    Search all visible records using a text/regex pattern (case-insensitive).

    Searches against json.dumps(record.value) for objects, str(record.value) for others.
    Returns sorted list of store indices.
    Raises ValueError for invalid regex patterns.
    """
    if not pattern:
        raise ValueError("Search pattern must not be empty")

    try:
        compiled = re.compile(pattern, re.IGNORECASE)
    except re.error as e:
        raise ValueError(f"Invalid regex: {e}") from e

    results = []
    for i in range(len(store)):
        record = store[i]
        if record.kind == KIND_OBJECT:
            text = json.dumps(record.value)
        else:
            text = str(record.value)
        if compiled.search(text):
            results.append(i)
    return results
