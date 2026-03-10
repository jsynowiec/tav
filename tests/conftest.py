# ABOUTME: pytest configuration and shared fixtures for tav tests
# ABOUTME: Provides reusable fixtures for JSONL data, temp files, and record stores.
import json
import pytest


@pytest.fixture
def jsonl_file(tmp_path):
    """Create a temporary JSONL file from a list of objects."""
    def _make(lines: list, filename: str = "test.jsonl") -> "pathlib.Path":
        path = tmp_path / filename
        path.write_text("\n".join(json.dumps(obj) for obj in lines) + "\n")
        return path
    return _make
