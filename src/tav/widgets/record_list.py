# ABOUTME: Virtual-scrolling record list widget for tav.
# ABOUTME: Renders JSONL records line-by-line using ScrollView.render_line for performance.
from __future__ import annotations

import json

from rich.segment import Segment
from rich.style import Style
from textual.geometry import Size
from textual.scroll_view import ScrollView
from textual.strip import Strip

from tav.loader import KIND_ARRAY, KIND_ERROR, KIND_OBJECT, KIND_PRIMITIVE
from tav.store import RecordStore

# Width of the line-number prefix column (digits + separator)
_LINE_NUM_WIDTH = 5
_SEPARATOR = " \u2502 "  # " │ "


class RecordList(ScrollView, can_focus=True):
    """Virtual-scrolling log-style record list."""

    DEFAULT_CSS = """
    RecordList {
        height: 1fr;
    }
    """

    BINDINGS = [
        ("j", "cursor_down", "Down"),
        ("k", "cursor_up", "Up"),
        ("down", "cursor_down", "Down"),
        ("up", "cursor_up", "Up"),
        ("home", "cursor_top", "Top"),
        ("end", "cursor_bottom", "Bottom"),
    ]

    def __init__(self, store: RecordStore, **kwargs) -> None:
        super().__init__(**kwargs)
        self._store = store
        self._cursor: int = 0

    def on_mount(self) -> None:
        # Set the virtual height to the number of records; width handled by the container.
        self.virtual_size = Size(self.size.width or 80, max(len(self._store), 1))

    def on_resize(self) -> None:
        self.virtual_size = Size(self.size.width or 80, max(len(self._store), 1))

    def render_line(self, y: int) -> Strip:
        """Render a single visible line.

        y is relative to the top of the visible area; add scroll_offset.y to get
        the absolute record index into the store.
        """
        scroll_x, scroll_y = self.scroll_offset
        record_index = y + scroll_y
        width = self.size.width

        if record_index >= len(self._store):
            return Strip.blank(width)

        record = self._store[record_index]
        is_cursor = record_index == self._cursor

        # Build prefix: right-justified line number + separator
        line_num = str(record.line_number).rjust(_LINE_NUM_WIDTH)
        prefix = line_num + _SEPARATOR

        # Build content string based on record kind
        if record.kind == KIND_OBJECT:
            content = json.dumps(record.value, separators=(",", ":"))
            content_style = Style(bold=True) if is_cursor else Style()
        elif record.kind == KIND_ERROR:
            content = f"[ERROR] {record.value}"
            content_style = Style(color="red")
        elif record.kind == KIND_ARRAY:
            content = json.dumps(record.value, separators=(",", ":"))
            content_style = Style(color="yellow")
        else:  # KIND_PRIMITIVE
            content = json.dumps(record.value)
            content_style = Style(color="cyan")

        full_line = prefix + content

        # Pad or truncate to widget width
        if len(full_line) >= width:
            full_line = full_line[: width - 1] + "\u2026"  # …
        else:
            full_line = full_line.ljust(width)

        prefix_len = len(prefix)

        if is_cursor:
            cursor_style = Style(reverse=True)
            segments = [Segment(full_line, cursor_style)]
        else:
            num_part = full_line[:_LINE_NUM_WIDTH]
            sep_part = full_line[_LINE_NUM_WIDTH:prefix_len]
            content_part = full_line[prefix_len:]
            segments = [
                Segment(num_part, Style(dim=True)),
                Segment(sep_part, Style(dim=True)),
                Segment(content_part, content_style),
            ]

        strip = Strip(segments, width)
        # Crop to account for horizontal scroll
        return strip.crop(scroll_x, scroll_x + width)

    # ------------------------------------------------------------------
    # Cursor movement actions
    # ------------------------------------------------------------------

    def action_cursor_down(self) -> None:
        if self._cursor < len(self._store) - 1:
            self._cursor += 1
            self._ensure_cursor_visible()
            self.refresh()

    def action_cursor_up(self) -> None:
        if self._cursor > 0:
            self._cursor -= 1
            self._ensure_cursor_visible()
            self.refresh()

    def action_cursor_top(self) -> None:
        self._cursor = 0
        self.scroll_to(y=0, animate=False)
        self.refresh()

    def action_cursor_bottom(self) -> None:
        self._cursor = max(0, len(self._store) - 1)
        self.scroll_to(y=self._cursor, animate=False)
        self.refresh()

    def _ensure_cursor_visible(self) -> None:
        """Scroll so the cursor row is within the visible area."""
        scroll_y = self.scroll_offset.y
        visible_height = self.size.height
        if self._cursor < scroll_y:
            self.scroll_to(y=self._cursor, animate=False)
        elif self._cursor >= scroll_y + visible_height:
            self.scroll_to(y=self._cursor - visible_height + 1, animate=False)
