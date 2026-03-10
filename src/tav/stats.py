# ABOUTME: Pure functions for computing statistics over a RecordStore.
# ABOUTME: Returns DataStats, TimeStats, and FieldStats — no UI imports.
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable, Any

from tav.loader import KIND_OBJECT
from tav.store import RecordStore


@dataclass
class TimeStats:
    record_count: int
    min_time: datetime | None
    max_time: datetime | None
    # time span in seconds (None if < 2 parseable records)
    span_seconds: float | None


@dataclass
class FieldStats:
    name: str
    present_count: int          # records containing this field
    total_count: int            # total records in input
    completeness: float         # present_count / total_count (0.0 to 1.0)
    value_type: str             # "numeric", "string", "boolean", "mixed", "null"
    cardinality: str            # "low" (<10), "medium" (10-100), "high" (>100)
    unique_count: int           # count of unique values
    value_counts: dict | None   # {json.dumps(value): count} for low/medium, None for high


@dataclass
class DataStats:
    total_count: int            # total records in dataset (all kinds)
    filtered_count: int         # records in current view
    object_count: int           # kind=object records (unfiltered)
    error_count: int            # kind=error records (unfiltered)
    time_stats: TimeStats | None
    field_stats: list[FieldStats]


def compute_stats(
    store: RecordStore,
    time_field: str | None,
    time_parser: Callable[[Any], datetime | None],
) -> DataStats:
    """Compute statistics over the current visible records in the store."""
    visible = [store[i] for i in range(len(store))]
    visible_objects = [r for r in visible if r.kind == KIND_OBJECT and isinstance(r.value, dict)]

    time_stats = _compute_time_stats(visible_objects, time_field, time_parser)
    field_stats = _compute_field_stats(visible_objects)

    return DataStats(
        total_count=store.total_count,
        filtered_count=len(store),
        object_count=store.object_count,
        error_count=store.error_count,
        time_stats=time_stats,
        field_stats=field_stats,
    )


def _compute_time_stats(
    objects: list,
    time_field: str | None,
    time_parser: Callable[[Any], datetime | None],
) -> TimeStats | None:
    if time_field is None:
        return None

    times: list[datetime] = []
    for rec in objects:
        raw = rec.value.get(time_field)
        dt = time_parser(raw)
        if dt is not None:
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            times.append(dt)

    if not times:
        return None

    min_time = min(times)
    max_time = max(times)
    span = (max_time - min_time).total_seconds() if len(times) >= 2 else None

    return TimeStats(
        record_count=len(times),
        min_time=min_time,
        max_time=max_time,
        span_seconds=span,
    )


def _python_type_to_value_type(value: Any) -> str:
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, (int, float)):
        return "numeric"
    if isinstance(value, str):
        return "string"
    if value is None:
        return "null"
    return "mixed"


def _compute_field_stats(objects: list) -> list[FieldStats]:
    if not objects:
        return []

    total = len(objects)

    # Collect all field names across all visible objects
    all_fields: set[str] = set()
    for rec in objects:
        all_fields.update(rec.value.keys())

    result: list[FieldStats] = []
    for field_name in sorted(all_fields):
        present_count = 0
        value_counts: dict[str, int] = {}
        type_set: set[str] = set()

        for rec in objects:
            if field_name not in rec.value:
                continue
            present_count += 1
            val = rec.value[field_name]
            type_set.add(_python_type_to_value_type(val))
            key = json.dumps(val, ensure_ascii=False)
            value_counts[key] = value_counts.get(key, 0) + 1

        completeness = present_count / total if total > 0 else 0.0

        if len(type_set) == 1:
            value_type = next(iter(type_set))
        else:
            value_type = "mixed"

        unique_count = len(value_counts)

        if unique_count < 10:
            cardinality = "low"
        elif unique_count <= 100:
            cardinality = "medium"
        else:
            cardinality = "high"

        result.append(FieldStats(
            name=field_name,
            present_count=present_count,
            total_count=total,
            completeness=completeness,
            value_type=value_type,
            cardinality=cardinality,
            unique_count=unique_count,
            value_counts=value_counts if cardinality != "high" else None,
        ))

    return result
