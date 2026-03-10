# ABOUTME: Virtual-scrolling record list widget for tav.
# ABOUTME: Renders JSONL records line-by-line using ScrollView.render_line for performance.
from __future__ import annotations

import json

from rich.segment import Segment
from rich.style import Style
from textual.binding import Binding
from textual.geometry import Size
from textual.message import Message
from textual.scroll_view import ScrollView
from textual.strip import Strip

from tav.loader import KIND_ARRAY, KIND_ERROR, KIND_OBJECT, KIND_PRIMITIVE, ParsedLine
from tav.store import RecordStore

# Width of the line-number prefix column (digits + separator)
_LINE_NUM_WIDTH = 5
_SEPARATOR = " \u2502 "  # " │ "

_STYLE_KEY = Style(color="cyan", bold=True)
_STYLE_STRING = Style(color="green")
_STYLE_NUMBER = Style(color="yellow")
_STYLE_BOOL = Style(color="red")
_STYLE_NULL = Style(color="bright_black")


def _plain_content_style(record) -> Style:
    """Return the plain (non-pretty) style for a record's content."""
    if record.kind == KIND_OBJECT:
        return Style()
    elif record.kind == KIND_ERROR:
        return Style(color="red")
    elif record.kind == KIND_ARRAY:
        return Style(color="yellow")
    else:  # KIND_PRIMITIVE
        return Style(color="cyan")


def _colorize_object(value: dict, max_width: int) -> list[Segment]:
    """Return inline colored segments for a JSON object, truncated to max_width chars."""
    segments: list[Segment] = []
    total = 0

    def _append(text: str, style: Style) -> bool:
        nonlocal total
        remaining = max_width - total
        if remaining <= 0:
            return False
        if len(text) > remaining:
            text = text[: remaining - 1] + "\u2026"
            segments.append(Segment(text, style))
            total = max_width
            return False
        segments.append(Segment(text, style))
        total += len(text)
        return True

    if not _append("{", Style()):
        return segments

    items = list(value.items())
    for i, (k, v) in enumerate(items):
        key_str = f'"{k}":'
        if not _append(key_str, _STYLE_KEY):
            break

        if isinstance(v, bool):
            val_str = "true" if v else "false"
            style = _STYLE_BOOL
        elif v is None:
            val_str = "null"
            style = _STYLE_NULL
        elif isinstance(v, str):
            val_str = f'"{v}"'
            style = _STYLE_STRING
        elif isinstance(v, (int, float)):
            val_str = json.dumps(v)
            style = _STYLE_NUMBER
        else:
            val_str = json.dumps(v, separators=(",", ":"))
            style = Style()

        if i < len(items) - 1:
            val_str += ","

        if not _append(val_str, style):
            break
    else:
        _append("}", Style())

    # Pad to fill the remaining width
    if total < max_width:
        segments.append(Segment(" " * (max_width - total), Style()))

    return segments


class RecordList(ScrollView, can_focus=True):
    """Virtual-scrolling log-style record list."""

    class RecordSelected(Message):
        """Posted when the user presses Enter on a record."""

        def __init__(self, record: ParsedLine) -> None:
            super().__init__()
            self.record = record

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
        Binding("t", "toggle_pretty", "Pretty", show=True),
        Binding("a", "toggle_line_mode", "All lines", show=True),
        Binding("o", "toggle_sort", "Sort", show=True),
        Binding("enter", "show_detail", "Detail", show=True),
    ]

    def __init__(self, store: RecordStore, **kwargs) -> None:
        super().__init__(**kwargs)
        self._store = store
        self._cursor: int = 0
        self._pretty: bool = False
        self._sorted: bool = False

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
        prefix_len = len(prefix)
        content_width = max(0, width - prefix_len)

        if is_cursor:
            cursor_style = Style(reverse=True)
            content = self._render_content_plain(record)
            full_line = prefix + content
            if len(full_line) >= width:
                full_line = full_line[: width - 1] + "\u2026"  # …
            else:
                full_line = full_line.ljust(width)
            segments = [Segment(full_line, cursor_style)]
        elif self._pretty and record.kind == KIND_OBJECT:
            prefix_segs = [
                Segment(line_num, Style(dim=True)),
                Segment(_SEPARATOR, Style(dim=True)),
            ]
            content_segs = _colorize_object(record.value, content_width)
            segments = prefix_segs + content_segs
        else:
            content = self._render_content_plain(record)
            full_line = prefix + content
            if len(full_line) >= width:
                full_line = full_line[: width - 1] + "\u2026"  # …
            else:
                full_line = full_line.ljust(width)
            content_style = _plain_content_style(record)
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

    def _render_content_plain(self, record) -> str:
        """Return a plain (unstyled) content string for a record."""
        if record.kind in (KIND_OBJECT, KIND_ARRAY):
            return json.dumps(record.value, separators=(",", ":"))
        elif record.kind == KIND_ERROR:
            return f"[ERROR] {record.value}"
        else:  # KIND_PRIMITIVE
            return json.dumps(record.value)

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

    # ------------------------------------------------------------------
    # Display mode actions
    # ------------------------------------------------------------------

    def action_toggle_pretty(self) -> None:
        self._pretty = not self._pretty
        self.refresh()

    def action_toggle_line_mode(self) -> None:
        self._store.toggle_line_mode()
        self._cursor = 0
        self.virtual_size = Size(self.size.width or 80, max(len(self._store), 1))
        self.scroll_to(y=0, animate=False)
        self.refresh()

    def action_toggle_sort(self) -> None:
        from tav.time_parse import parse_timestamp

        time_field = self.app.time_field  # type: ignore[attr-defined]
        if time_field is None:
            self.app.notify("No time field detected")
            return
        if not self._sorted:
            self._store.sort_by_time(time_field, parse_timestamp)
        else:
            self._store.reset_sort()
        self._sorted = not self._sorted
        self._cursor = 0
        self.virtual_size = Size(self.size.width or 80, max(len(self._store), 1))
        self.scroll_to(y=0, animate=False)
        self.refresh()

    def action_show_detail(self) -> None:
        if len(self._store) == 0:
            return
        record = self._store[self._cursor]
        self.post_message(RecordList.RecordSelected(record))
