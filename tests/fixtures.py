# ABOUTME: Sample data for tav integration tests.
# ABOUTME: Provides curated sample records used across test modules.
import json


def mixed_jsonl_lines() -> list[str]:
    """A mix of objects, primitives, arrays, blank lines, and invalid JSON."""
    return [
        json.dumps({"timestamp": "2024-01-01T00:00:00Z", "val": 1}),
        "",  # blank line
        json.dumps({"timestamp": "2024-01-01T00:01:00Z", "val": 2}),
        json.dumps(42),  # primitive
        json.dumps([1, 2, 3]),  # array
        "not valid json {",  # invalid
        "   ",  # whitespace-only
        json.dumps({"timestamp": "2024-01-01T00:02:00Z", "val": 3}),
    ]
