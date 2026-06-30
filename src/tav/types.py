# ABOUTME: Shared type aliases for tav.
# ABOUTME: Defines JsonValue for parsed JSONL records.
from typing import TypeAlias

JsonValue: TypeAlias = (
    str | int | float | bool | None | dict[str, "JsonValue"] | list["JsonValue"]
)
