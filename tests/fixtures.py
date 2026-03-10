# ABOUTME: Test data generators for tav tests
# ABOUTME: Provides fixed-seed random JSONL data and curated sample records.
import json
import random
from datetime import datetime, timezone, timedelta


def sensor_records(count: int = 100, seed: int = 42) -> list[dict]:
    """IoT sensor readings with ISO 8601 timestamps."""
    rng = random.Random(seed)
    base = datetime(2024, 1, 1, tzinfo=timezone.utc)
    records = []
    for i in range(count):
        ts = base + timedelta(seconds=i * 60)
        record = {
            "timestamp": ts.isoformat(),
            "sensor_id": f"sensor_{rng.randint(1, 5)}",
            "temperature": round(rng.uniform(18.0, 35.0), 2),
            "humidity": round(rng.uniform(30.0, 90.0), 2),
        }
        if rng.random() > 0.7:
            record["pressure"] = round(rng.uniform(950.0, 1050.0), 2)
        records.append(record)
    return records


def sparse_records(count: int = 50, seed: int = 99) -> list[dict]:
    """Heterogeneous records with varying schemas (sparse)."""
    rng = random.Random(seed)
    base = datetime(2024, 6, 1, tzinfo=timezone.utc)
    event_types = ["play", "pause", "seek", "stop", "volume_change"]
    records = []
    for i in range(count):
        ts = base + timedelta(seconds=i * 30)
        event = rng.choice(event_types)
        record: dict = {"ts": ts.isoformat(), "event": event}
        if event == "play":
            record["track_id"] = f"track_{rng.randint(100, 999)}"
        elif event == "seek":
            record["position_ms"] = rng.randint(0, 240000)
        elif event == "volume_change":
            record["volume"] = rng.randint(0, 100)
        records.append(record)
    return records


def epoch_records(count: int = 20, seed: int = 7) -> list[dict]:
    """Records with Unix epoch timestamps (seconds)."""
    rng = random.Random(seed)
    base_ts = 1704067200  # 2024-01-01 00:00:00 UTC
    records = []
    for i in range(count):
        records.append({
            "time": base_ts + i * 300 + rng.randint(0, 60),
            "value": round(rng.uniform(0.0, 100.0), 3),
            "source": rng.choice(["alpha", "beta", "gamma"]),
        })
    return records


def mixed_jsonl_lines(seed: int = 13) -> list[str]:
    """A mix of objects, primitives, arrays, blank lines, and invalid JSON."""
    rng = random.Random(seed)
    return [
        json.dumps({"timestamp": "2024-01-01T00:00:00Z", "val": 1}),
        "",  # blank line
        json.dumps({"timestamp": "2024-01-01T00:01:00Z", "val": 2}),
        json.dumps(42),          # primitive
        json.dumps([1, 2, 3]),   # array
        "not valid json {",      # invalid
        "   ",                   # whitespace-only
        json.dumps({"timestamp": "2024-01-01T00:02:00Z", "val": 3}),
    ]
