# ABOUTME: Virtual-scrolling record list widget for tav.
# ABOUTME: Renders JSONL records line-by-line using ScrollView.render_line for performance.
import json
from typing import TYPE_CHECKING

from rich.segment import Segment
from rich.style import Style
from textual.binding import Binding
from textual.geometry import Size
from textual.message import Message
from textual.scroll_view import ScrollView
from textual.strip import Strip

from tav.loader import KIND_ARRAY, KIND_ERROR, KIND_OBJECT, ParsedLine
from tav.store import RecordStore

if TYPE_CHECKING:
    from tav.app import TavApp

# Width of the line-number prefix column (digits + separator)
_LINE_NUM_WIDTH = 5
_SEPARATOR = " \u2502 "  # " │ "
_SCROLL_STEP = 8

_STYLE_KEY = Style(color="cyan", bold=True)
_STYLE_STRING = Style(color="green")
_STYLE_NUMBER = Style(color="yellow")
_STYLE_BOOL = Style(color="red")
_STYLE_NULL = Style(color="bright_black")


def _is_field_visible(
    path: tuple[str, ...], visible_fields: set[tuple[str, ...]]
) -> bool:
    """Return True if path is selected or any descendant path is selected."""
    if path in visible_fields:
        return True
    # Check if any selected path starts with this path (descendant)
    prefix_len = len(path)
    return any(len(f) > prefix_len and f[:prefix_len] == path for f in visible_fields)


def _colorize_value(
    value,
    max_width: int,
    visible_fields: set[tuple[str, ...]] | None = None,
) -> list[Segment]:
    """Return inline colored segments for any JSON value, truncated to max_width chars."""
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

    _MAX_DEPTH = 20

    def _render(val, path: tuple[str, ...] = (), depth: int = 0) -> bool:
        if depth > _MAX_DEPTH:
            return _append("...", Style(dim=True))
        if isinstance(val, dict):
            if not _append("{", Style()):
                return False
            items = list(val.items())
            if visible_fields is not None:
                items = [
                    (k, v)
                    for k, v in items
                    if _is_field_visible(path + (k,), visible_fields)
                ]
            for i, (k, v) in enumerate(items):
                if not _append(f'"{k}":', _STYLE_KEY):
                    return False
                if not _render(v, path + (k,), depth + 1):
                    return False
                if i < len(items) - 1:
                    if not _append(",", Style()):
                        return False
            return _append("}", Style())
        elif isinstance(val, list):
            if not _append("[", Style()):
                return False
            for i, item in enumerate(val):
                if not _render(item, path, depth + 1):
                    return False
                if i < len(val) - 1:
                    if not _append(",", Style()):
                        return False
            return _append("]", Style())
        elif isinstance(val, bool):
            return _append("true" if val else "false", _STYLE_BOOL)
        elif val is None:
            return _append("null", _STYLE_NULL)
        elif isinstance(val, str):
            return _append(f'"{val}"', _STYLE_STRING)
        elif isinstance(val, (int, float)):
            return _append(json.dumps(val), _STYLE_NUMBER)
        else:
            return _append(str(val), Style())

    _render(value)

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

    class DisplayChanged(Message):
        """Posted when line mode or sort order changes, invalidating search indices."""

    DEFAULT_CSS = """
    RecordList {
        height: 1fr;
    }
    """

    BINDINGS = [
        Binding("j", "cursor_down", "Down"),
        Binding("k", "cursor_up", "Up"),
        Binding("down", "cursor_down", "Down"),
        Binding("up", "cursor_up", "Up"),
        Binding("left", "scroll_left", "Left"),
        Binding("right", "scroll_right", "Right"),
        Binding("h", "scroll_left", "Left"),
        Binding("l", "scroll_right", "Right"),
        Binding("home", "cursor_top", "Top"),
        Binding("end", "cursor_bottom", "Bottom"),
        Binding("a", "toggle_line_mode", "All lines", show=True),
        Binding("o", "toggle_sort", "Sort", show=True),
        Binding("enter", "show_detail", "Detail", show=True),
    ]

    def __init__(self, store: RecordStore, **kwargs) -> None:
        super().__init__(**kwargs)
        self._store = store
        self._cursor: int = 0
        self._sorted: bool = False
        self._max_content_width: int = self._compute_max_content_width()

    @property
    def app(self) -> "TavApp":
        return super().app  # type: ignore[return-value]

    def _compute_max_content_width(self) -> int:
        """Scan store to find the widest record content width."""
        prefix_len = _LINE_NUM_WIDTH + len(_SEPARATOR)
        max_w = 0
        for i in range(len(self._store)):
            record = self._store[i]
            content = self._render_content_plain(record)
            line_w = prefix_len + len(content)
            if line_w > max_w:
                max_w = line_w
        return max_w

    def on_mount(self) -> None:
        self.virtual_size = Size(
            max(self._max_content_width, self.size.width or 80),
            max(len(self._store), 1),
        )

    def on_resize(self) -> None:
        self.virtual_size = Size(
            max(self._max_content_width, self.size.width or 80),
            max(len(self._store), 1),
        )

    def render_line(self, y: int) -> Strip:
        """Render a single visible line.

        y is relative to the top of the visible area; add scroll_offset.y to get
        the absolute record index into the store.
        """
        scroll_x, scroll_y = self.scroll_offset
        record_index = y + scroll_y
        width = self.size.width
        virtual_width = self.virtual_size.width

        if record_index >= len(self._store):
            return Strip.blank(width)

        record = self._store[record_index]
        is_cursor = record_index == self._cursor

        # Build prefix: right-justified line number + separator
        line_num = str(record.line_number).rjust(_LINE_NUM_WIDTH)
        prefix = line_num + _SEPARATOR
        prefix_len = len(prefix)
        content_width = max(0, virtual_width - prefix_len)

        prefix_segs = [
            Segment(line_num, Style(dim=True)),
            Segment(_SEPARATOR, Style(dim=True)),
        ]

        if record.kind == KIND_ERROR:
            error_style = Style(color="red")
            content = f"[ERROR] {record.value}"
            if len(content) > content_width:
                content = content[: content_width - 1] + "\u2026"
            else:
                content = content.ljust(content_width)
            content_segs = [Segment(content, error_style)]
        else:
            content_segs = _colorize_value(
                record.value, content_width, self._store.visible_fields
            )

        segments = prefix_segs + content_segs

        if is_cursor:
            cursor_style = Style(reverse=True)
            segments = [Segment(s.text, s.style + cursor_style) for s in segments]

        strip = Strip(segments, virtual_width)
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

    def action_toggle_line_mode(self) -> None:
        self._store.toggle_line_mode()
        self._cursor = 0
        self._max_content_width = self._compute_max_content_width()
        self.virtual_size = Size(
            max(self._max_content_width, self.size.width or 80),
            max(len(self._store), 1),
        )
        self.scroll_to(y=0, animate=False)
        self.refresh()
        self.post_message(RecordList.DisplayChanged())

    def action_toggle_sort(self) -> None:
        time_field = self.app.time_field
        if time_field is None:
            self.app.notify("No time field detected")
            return
        if not self._sorted:
            self._store.sort_by_time(time_field, self.app.time_parser)
        else:
            self._store.reset_sort()
        self._sorted = not self._sorted
        self._cursor = 0
        self._max_content_width = self._compute_max_content_width()
        self.virtual_size = Size(
            max(self._max_content_width, self.size.width or 80),
            max(len(self._store), 1),
        )
        self.scroll_to(y=0, animate=False)
        self.refresh()
        self.post_message(RecordList.DisplayChanged())

    def action_scroll_left(self) -> None:
        self.scroll_to(x=max(0, self.scroll_offset.x - _SCROLL_STEP), animate=False)
        self.refresh()

    def action_scroll_right(self) -> None:
        max_x = max(0, self.virtual_size.width - self.size.width)
        self.scroll_to(x=min(self.scroll_offset.x + _SCROLL_STEP, max_x), animate=False)
        self.refresh()

    def scroll_to_field(self, field_name: str) -> None:
        """Scroll horizontally so that field_name is visible in the current cursor row."""
        if len(self._store) == 0:
            return
        record = self._store[self._cursor]
        content = self._render_content_plain(record)
        needle = f'"{field_name}":'
        pos = content.find(needle)
        if pos == -1:
            return
        prefix_len = _LINE_NUM_WIDTH + len(_SEPARATOR)
        offset = prefix_len + pos
        self.scroll_to(x=offset, animate=False)
        self.refresh()

    def reset_cursor(self) -> None:
        """Move the cursor to the top of the list."""
        self._cursor = 0

    def recompute_content_width(self) -> None:
        """Rescan the store and update the maximum content width."""
        self._max_content_width = self._compute_max_content_width()

    def jump_to_index(self, index: int) -> None:
        """Move cursor and scroll to the given store index."""
        self._cursor = index
        self.scroll_to(y=index, animate=False)
        self.refresh()

    def action_show_detail(self) -> None:
        if len(self._store) == 0:
            return
        record = self._store[self._cursor]
        self.post_message(RecordList.RecordSelected(record))
