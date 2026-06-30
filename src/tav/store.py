# ABOUTME: In-memory record store for JSONL time-series data with filtering, sorting, and line mode.
# ABOUTME: Wraps a list of ParsedLine records and exposes a filtered/sorted view.
from typing import Callable, Any

from tav.loader import ParsedLine, KIND_OBJECT, KIND_ERROR

# Nested dict representing the union of all field paths across records.
# Keys are field names; values are subtrees (empty dict for leaf fields).
FieldTree = dict[str, "FieldTree"]


def _merge_fields(obj: dict, tree: FieldTree, depth: int, max_depth: int) -> None:
    """Recursively merge keys from obj into tree up to max_depth."""
    if depth > max_depth:
        return
    for key, val in obj.items():
        if key not in tree:
            tree[key] = {}
        if isinstance(val, dict) and depth < max_depth:
            _merge_fields(val, tree[key], depth + 1, max_depth)
        elif isinstance(val, list) and depth < max_depth:
            for item in val:
                if isinstance(item, dict):
                    _merge_fields(item, tree[key], depth + 1, max_depth)


class RecordStore:
    def __init__(self, lines: list[ParsedLine]) -> None:
        self._source = list(lines)
        self._all_lines_mode = False
        self._predicate: Callable[[ParsedLine], bool] | None = None
        self._sort_key: list[int] | None = None  # permutation indices into base list
        self._cache: list[ParsedLine] | None = None
        self._visible_fields: set[tuple[str, ...]] | None = None
        self._object_count = sum(1 for r in self._source if r.kind == KIND_OBJECT)
        self._error_count = sum(1 for r in self._source if r.kind == KIND_ERROR)

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

    @property
    def predicate(self) -> Callable[[ParsedLine], bool] | None:
        return self._predicate

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

    def field_tree(self, max_depth: int = 5) -> FieldTree:
        """Return a nested dict of all field paths across KIND_OBJECT records."""
        tree: FieldTree = {}
        for rec in self._source:
            if rec.kind == KIND_OBJECT and isinstance(rec.value, dict):
                _merge_fields(rec.value, tree, depth=1, max_depth=max_depth)
        return tree

    @property
    def visible_fields(self) -> set[tuple[str, ...]] | None:
        return self._visible_fields

    def set_visible_fields(self, fields: set[tuple[str, ...]] | None) -> None:
        self._visible_fields = fields

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
                return (1, idx)
            return (0, dt)

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
        return self._object_count

    @property
    def error_count(self) -> int:
        return self._error_count

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
