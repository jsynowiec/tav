# ABOUTME: Tests for the tav CLI entry point (argparse-based).
# ABOUTME: Uses subprocess with TAV_NO_UI=1 to skip launching the TUI.
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def run_tav(*args, input_text=None, env_extra=None):
    """Run the tav CLI via uv and return the CompletedProcess result."""
    env = {**os.environ, "TAV_NO_UI": "1", **(env_extra or {})}
    return subprocess.run(
        ["uv", "run", "tav"] + list(args),
        capture_output=True,
        text=True,
        input=input_text,
        cwd=PROJECT_ROOT,
        env=env,
    )


def make_jsonl(tmp_path, records):
    """Write a list of dicts as a JSONL file and return its path."""
    p = tmp_path / "data.jsonl"
    p.write_text("\n".join(json.dumps(r) for r in records) + "\n")
    return p


# ---------------------------------------------------------------------------
# Basic flags
# ---------------------------------------------------------------------------


def test_version_flag():
    result = run_tav("--version")
    assert result.returncode == 0
    assert "0.1.0" in result.stdout


def test_help_flag():
    result = run_tav("--help")
    assert result.returncode == 0
    assert "usage" in result.stdout.lower()


# ---------------------------------------------------------------------------
# File input error cases
# ---------------------------------------------------------------------------


def test_file_not_found():
    result = run_tav("/nonexistent/path/to/data.jsonl")
    assert result.returncode == 1
    assert "Error: file not found" in result.stderr


def test_directory_as_input(tmp_path):
    result = run_tav(str(tmp_path))
    assert result.returncode == 1
    assert "Error: not a file" in result.stderr


# ---------------------------------------------------------------------------
# Successful file loading
# ---------------------------------------------------------------------------


def test_valid_jsonl_file(tmp_path):
    p = make_jsonl(tmp_path, [{"timestamp": "2024-01-01T00:00:00Z", "value": 1}])
    result = run_tav(str(p))
    assert result.returncode == 0


def test_empty_file_exits_zero(tmp_path):
    p = tmp_path / "empty.jsonl"
    p.write_text("")
    result = run_tav(str(p))
    assert result.returncode == 0
    assert result.stderr  # some warning printed


# ---------------------------------------------------------------------------
# Stdin input
# ---------------------------------------------------------------------------


def test_stdin_input():
    jsonl = json.dumps({"timestamp": "2024-01-01T00:00:00Z", "value": 42}) + "\n"
    result = run_tav("-", input_text=jsonl)
    assert result.returncode == 0
    assert "Reading from stdin" in result.stderr


def test_stdin_input_no_arg():
    jsonl = json.dumps({"timestamp": "2024-01-01T00:00:00Z", "value": 42}) + "\n"
    result = run_tav(input_text=jsonl)
    assert result.returncode == 0
    assert "Reading from stdin" in result.stderr


# ---------------------------------------------------------------------------
# --time-field flag
# ---------------------------------------------------------------------------


def test_time_field_flag_valid(tmp_path):
    p = make_jsonl(tmp_path, [{"ts": "2024-01-01T00:00:00Z", "v": 1}])
    result = run_tav(str(p), "--time-field", "ts")
    assert result.returncode == 0


def test_time_field_flag_warns_no_match(tmp_path):
    p = make_jsonl(tmp_path, [{"ts": "2024-01-01T00:00:00Z", "v": 1}])
    result = run_tav(str(p), "--time-field", "nonexistent_field")
    assert result.returncode == 0
    assert result.stderr  # warning printed


def test_time_field_dollar_prefix_normalized(tmp_path):
    """$.timestamp should be stripped to 'timestamp' and match without warning."""
    p = make_jsonl(tmp_path, [{"timestamp": "2024-01-01T00:00:00Z", "value": 1}])
    result = run_tav(str(p), "--time-field", "$.timestamp")
    assert result.returncode == 0
    assert "did not match" not in result.stderr


# ---------------------------------------------------------------------------
# --stats flag
# ---------------------------------------------------------------------------


def test_stats_flag(tmp_path):
    p = make_jsonl(tmp_path, [{"timestamp": "2024-01-01T00:00:00Z", "value": 1}])
    result = run_tav(str(p), "--stats")
    assert result.returncode == 0


# ---------------------------------------------------------------------------
# --timezone flag
# ---------------------------------------------------------------------------


def test_timezone_flag_valid(tmp_path):
    p = make_jsonl(tmp_path, [{"timestamp": "2024-01-01T00:00:00", "value": 1}])
    result = run_tav(str(p), "--timezone", "Europe/Warsaw")
    assert result.returncode == 0


def test_timezone_flag_invalid(tmp_path):
    p = make_jsonl(tmp_path, [{"timestamp": "2024-01-01T00:00:00", "value": 1}])
    result = run_tav(str(p), "--timezone", "Not/A/Timezone")
    assert result.returncode == 1
    assert "unknown timezone" in result.stderr
