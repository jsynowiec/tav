# ABOUTME: JSONL file loader that parses each line and categorizes it by JSON type.
# ABOUTME: Returns a LoadResult with ParsedLine records, preserving 1-based line numbers.
import json
from dataclasses import dataclass, field
from typing import TextIO

from tav.types import JsonValue

KIND_OBJECT = "object"
KIND_PRIMITIVE = "primitive"
KIND_ARRAY = "array"
KIND_ERROR = "error"


@dataclass
class ParsedLine:
    line_number: int
    value: JsonValue
    kind: str
    error: str | None = None


@dataclass
class LoadResult:
    records: list[ParsedLine] = field(default_factory=list)


def load_lines(source: TextIO) -> LoadResult:
    records: list[ParsedLine] = []
    for line_number, raw in enumerate(source, start=1):
        # Strip BOM from the very first line
        if line_number == 1:
            raw = raw.removeprefix("\ufeff")
        line = raw.rstrip("\r\n")
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            records.append(
                ParsedLine(
                    line_number=line_number,
                    value=line,
                    kind=KIND_ERROR,
                    error=str(exc),
                )
            )
            continue

        if isinstance(value, dict):
            kind = KIND_OBJECT
        elif isinstance(value, list):
            kind = KIND_ARRAY
        else:
            kind = KIND_PRIMITIVE

        records.append(ParsedLine(line_number=line_number, value=value, kind=kind))

    return LoadResult(records=records)
