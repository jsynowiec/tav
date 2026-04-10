# ABOUTME: Auto-detects which top-level field in JSONL records holds the timestamp.
# ABOUTME: Uses name heuristics first, then falls back to value-parse heuristics.
from tav.time_parse import parse_timestamp

_CANONICAL_NAMES: frozenset[str] = frozenset({
    "timestamp",
    "time",
    "ts",
    "datetime",
    "date",
    "created_at",
    "updated_at",
    "@timestamp",
})


def detect_time_field(records: list[dict], sample_size: int = 20) -> str | None:
    """Return the name of the top-level field most likely to hold timestamps.

    Scans the first `sample_size` records.  Returns None if no field is found.
    """
    sample = records[:sample_size]
    if not sample:
        return None

    result = _detect_by_name(sample)
    if result is not None:
        return result

    return _detect_by_value(sample)


# ---------------------------------------------------------------------------
# Stage 1: name heuristic
# ---------------------------------------------------------------------------

def _detect_by_name(sample: list[dict]) -> str | None:
    """Return the best name-matched field, or None."""
    # Collect all top-level keys that appear in the sample.
    candidate_keys: set[str] = set()
    for record in sample:
        candidate_keys.update(record.keys())

    # Keep only keys whose lowercase form matches a canonical name.
    name_matches: list[str] = [
        key for key in candidate_keys if key.lower() in _CANONICAL_NAMES
    ]
    if not name_matches:
        return None

    # Count parseable values for each matching key.
    best_key: str | None = None
    best_count: int = 0
    for key in name_matches:
        count = sum(
            1
            for record in sample
            if key in record and parse_timestamp(record[key]) is not None
        )
        if count > best_count:
            best_count = count
            best_key = key

    # Require at least one parseable value.
    return best_key if best_count > 0 else None


# ---------------------------------------------------------------------------
# Stage 2: value heuristic
# ---------------------------------------------------------------------------

def _detect_by_value(sample: list[dict]) -> str | None:
    """Return the field with the highest parse-success rate (>= 50%), or None."""
    # Collect all top-level keys across the sample.
    candidate_keys: set[str] = set()
    for record in sample:
        candidate_keys.update(record.keys())

    best_key: str | None = None
    best_rate: float = 0.0

    for key in candidate_keys:
        records_with_key = [r for r in sample if key in r]
        if not records_with_key:
            continue
        parseable = sum(
            1 for r in records_with_key if parse_timestamp(r[key]) is not None
        )
        rate = parseable / len(records_with_key)
        if rate >= 0.5 and rate > best_rate:
            best_rate = rate
            best_key = key

    return best_key
