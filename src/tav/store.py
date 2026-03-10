# ABOUTME: In-memory record store for JSONL time-series data with filtering, sorting, and line mode.
# ABOUTME: Wraps a list of ParsedLine records and exposes a filtered/sorted view.
from __future__ import annotations

from typing import Callable, Any

from tav.loader import ParsedLine, KIND_OBJECT


class RecordStore:
    def __init__(self, lines: list[ParsedLine]) -> None:
        self._source = list(lines)
        self._all_lines_mode = False
        self._predicate: Callable[[ParsedLine], bool] | None = None
        self._sort_key: list[int] | None = None  # permutation indices into base list
        self._cache: list[ParsedLine] | None = None

    # ------------------------------------------------------------------
    # Dunder protocol
    # ------------------------------------------------------------------

    def __len__(self) -> int:
        return len(self._visible())

    def __getitem__(self, index: int) -> ParsedLine:
        return self._visible()[index]

    # ------------------------------------------------------------------
    # Mode
    # ------------------------------------------------------------------

    def toggle_line_mode(self) -> None:
        self._all_lines_mode = not self._all_lines_mode
        self._invalidate()

    # ------------------------------------------------------------------
    # Filtering
    # ------------------------------------------------------------------

    def apply_filter(self, predicate: Callable[[ParsedLine], bool]) -> None:
        self._predicate = predicate
        self._invalidate()

    def clear_filter(self) -> None:
        self._predicate = None
        self._invalidate()

    # ------------------------------------------------------------------
    # Fields
    # ------------------------------------------------------------------

    def all_fields(self) -> set[str]:
        fields: set[str] = set()
        for rec in self._source:
            if rec.kind == KIND_OBJECT and isinstance(rec.value, dict):
                fields.update(rec.value.keys())
        return fields

    # ------------------------------------------------------------------
    # Sorting
    # ------------------------------------------------------------------

    def sort_by_time(self, time_field: str, parser: Callable[[Any], Any]) -> None:
        """Sort the base list by parsed timestamp; unparseable records go last."""
        def sort_key(item):
            idx, rec = item
            if rec.kind == KIND_OBJECT and isinstance(rec.value, dict):
                dt = parser(rec.value.get(time_field))
            else:
                dt = None
            if dt is None:
                return (1, 0, idx)
            # Separate aware and naive to avoid TypeError on comparison.
            # Aware (UTC) records sort before naive records.
            if dt.tzinfo is not None:
                return (0, 0, dt)
            return (0, 1, dt)

        indexed = list(enumerate(self._source))
        indexed.sort(key=sort_key)
        self._sort_key = [original_idx for original_idx, _ in indexed]
        self._invalidate()

    def reset_sort(self) -> None:
        self._sort_key = None
        self._invalidate()

    # ------------------------------------------------------------------
    # Count properties
    # ------------------------------------------------------------------

    @property
    def total_count(self) -> int:
        return len(self._source)

    @property
    def object_count(self) -> int:
        return sum(1 for r in self._source if r.kind == KIND_OBJECT)

    @property
    def error_count(self) -> int:
        from tav.loader import KIND_ERROR
        return sum(1 for r in self._source if r.kind == KIND_ERROR)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _base(self) -> list[ParsedLine]:
        """Return source records in current sort order."""
        if self._sort_key is not None:
            return [self._source[i] for i in self._sort_key]
        return self._source

    def _invalidate(self) -> None:
        self._cache = None

    def _visible(self) -> list[ParsedLine]:
        """Apply mode and filter to the sorted base list."""
        if self._cache is not None:
            return self._cache
        records = self._base()
        if not self._all_lines_mode:
            records = [r for r in records if r.kind == KIND_OBJECT]
        if self._predicate is not None:
            records = [r for r in records if self._predicate(r)]
        self._cache = records
        return self._cache
