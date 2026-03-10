# ABOUTME: Main data view screen — shows JSONL records in a scrollable list.
# ABOUTME: Composes Header, RecordList, CommandBar, and Footer with keybinding hints.
from textual.app import ComposeResult
from textual.binding import Binding
from textual.geometry import Size
from textual.screen import Screen
from textual.widgets import Footer, Header

from tav.loader import KIND_OBJECT
from tav.widgets.command_bar import CommandBar
from tav.widgets.field_nav import FieldNav
from tav.widgets.help_overlay import HelpOverlay
from tav.widgets.record_detail import RecordDetail
from tav.widgets.record_list import RecordList


class DataViewScreen(Screen):
    """Primary screen showing the record list."""

    BINDINGS = [
        Binding("colon", "open_command", "Filter"),
        Binding("slash", "open_search", "Search"),
        Binding("question_mark", "open_help", "Help"),
        Binding("g", "open_field_nav", "Go to field"),
        Binding("s", "toggle_stats", "Stats"),
        Binding("escape", "handle_escape", "Close"),
        Binding("n", "next_match", "Next match"),
        Binding("N", "prev_match", "Prev match", show=False),
    ]

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._active_filter: str | None = None
        self._match_indices: list[int] = []
        self._match_cursor: int = -1
        self._search_active: bool = False
        self._overlay_visible: bool = False

    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)
        yield RecordList(self.app.store)  # type: ignore[attr-defined]
        yield Footer()
        yield CommandBar()

    def on_mount(self) -> None:
        store = self.app.store  # type: ignore[attr-defined]
        source_name = self.app.source_name  # type: ignore[attr-defined]
        self.app.title = "tav"
        self.app.sub_title = f"{source_name}  {len(store)} records"

    # ------------------------------------------------------------------
    # Record selection
    # ------------------------------------------------------------------

    def on_record_list_record_selected(self, message: RecordList.RecordSelected) -> None:
        self.app.push_screen(RecordDetail(message.record))

    # ------------------------------------------------------------------
    # Display change (line mode / sort toggle)
    # ------------------------------------------------------------------

    def on_record_list_display_changed(self, message: RecordList.DisplayChanged) -> None:
        self._clear_search()
        self._refresh_record_list()

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def action_open_command(self) -> None:
        self.query_one(CommandBar).activate_command()

    def action_open_search(self) -> None:
        self.query_one(CommandBar).activate_search()

    def action_open_help(self) -> None:
        self._overlay_visible = True
        self.app.push_screen(HelpOverlay(), callback=self._on_overlay_dismissed)

    def action_open_field_nav(self) -> None:
        fields = sorted(self.app.store.all_fields())  # type: ignore[attr-defined]
        if not fields:
            self.app.notify("No fields detected", severity="warning")
            return
        self._overlay_visible = True
        self.app.push_screen(FieldNav(fields), callback=self._on_field_nav_dismissed)

    def action_toggle_stats(self) -> None:
        from tav.screens.stats_view import StatsViewScreen
        self.app.push_screen(StatsViewScreen())

    def action_next_match(self) -> None:
        if not self._match_indices:
            return
        self._match_cursor = (self._match_cursor + 1) % len(self._match_indices)
        self._jump_to_match()

    def action_prev_match(self) -> None:
        if not self._match_indices:
            return
        self._match_cursor = (self._match_cursor - 1) % len(self._match_indices)
        self._jump_to_match()

    def action_handle_escape(self) -> None:
        """
        Escape precedence:
        1. Dismiss top overlay (HelpOverlay, FieldNav, RecordDetail) — handled by ModalScreen itself
        2. Hide CommandBar if visible
        3. Clear search highlights
        4. Clear active filter
        """
        bar = self.query_one(CommandBar)
        if bar.display:
            bar.display = False
            self.post_message(CommandBar.Dismissed())
            return

        if self._search_active:
            self._clear_search()
            self._refresh_record_list()
            self._focus_record_list()
            return

        if self._active_filter is not None:
            self.app.store.clear_filter()  # type: ignore[attr-defined]
            self._active_filter = None
            self._refresh_record_list()
            store = self.app.store  # type: ignore[attr-defined]
            source_name = self.app.source_name  # type: ignore[attr-defined]
            self.app.sub_title = f"{source_name}  {len(store)} records"
            self._focus_record_list()

    # ------------------------------------------------------------------
    # Overlay callbacks
    # ------------------------------------------------------------------

    def _on_overlay_dismissed(self, result=None) -> None:
        self._overlay_visible = False

    def _on_field_nav_dismissed(self, result: str | None) -> None:
        self._overlay_visible = False
        if result:
            self.query_one(RecordList).scroll_to_field(result)

    # ------------------------------------------------------------------
    # CommandBar message handlers
    # ------------------------------------------------------------------

    def on_command_bar_command_submitted(self, message: CommandBar.CommandSubmitted) -> None:
        """Apply JMESPath filter or time range command."""
        self._apply_command(message.expression)
        self._focus_record_list()

    def on_command_bar_search_submitted(self, message: CommandBar.SearchSubmitted) -> None:
        """Apply text/regex search and highlight matches."""
        self._apply_search(message.pattern)
        self._focus_record_list()

    def on_command_bar_dismissed(self, message: CommandBar.Dismissed) -> None:
        """CommandBar dismissed with Escape — do nothing (don't clear active filter)."""
        self._focus_record_list()

    # ------------------------------------------------------------------
    # Filter and search application
    # ------------------------------------------------------------------

    @property
    def active_filter(self) -> str | None:
        return self._active_filter

    def _focus_record_list(self) -> None:
        self.query_one(RecordList).focus()

    def _apply_command(self, expression: str) -> None:
        """Parse expression and apply as filter or time range to the store."""
        from tav.query import filter_records

        if expression.lower().startswith("after:"):
            self._apply_time_filter(expression[6:].strip(), "after")
            return
        if expression.lower().startswith("before:"):
            self._apply_time_filter(expression[7:].strip(), "before")
            return

        store = self.app.store  # type: ignore[attr-defined]
        store.clear_filter()
        try:
            match_indices = filter_records(store, expression)
        except ValueError as e:
            self.app.notify(f"Invalid filter: {e}", severity="error")
            self._active_filter = None
            self._refresh_record_list()
            source_name = self.app.source_name  # type: ignore[attr-defined]
            self.app.sub_title = f"{source_name}  {len(store)} records"
            return

        matched_line_nums = {store[i].line_number for i in match_indices}
        store.apply_filter(lambda r: r.line_number in matched_line_nums)
        self._active_filter = expression
        self._clear_search()
        self._refresh_record_list()
        source_name = self.app.source_name  # type: ignore[attr-defined]
        self.app.sub_title = f"{source_name}  {len(store)} records — :{self._active_filter}"

    def _apply_time_filter(self, value: str, direction: str) -> None:
        """Filter records to those after/before the given timestamp."""
        from tav.time_parse import parse_timestamp

        dt = parse_timestamp(value)
        if dt is None:
            self.app.notify(f"Cannot parse timestamp: {value!r}", severity="error")
            return
        if self.app.time_field is None:  # type: ignore[attr-defined]
            self.app.notify("No time field detected", severity="warning")
            return

        time_field = self.app.time_field  # type: ignore[attr-defined]

        def predicate(record) -> bool:
            if record.kind != KIND_OBJECT:
                return False
            val = record.value.get(time_field)
            if val is None:
                return False
            rec_dt = parse_timestamp(val)
            if rec_dt is None:
                return False
            # Only compare when both are tz-aware or both are naive
            if rec_dt.tzinfo is not None and dt.tzinfo is not None:
                return rec_dt > dt if direction == "after" else rec_dt < dt
            if rec_dt.tzinfo is None and dt.tzinfo is None:
                return rec_dt > dt if direction == "after" else rec_dt < dt
            return False  # mixed tz/naive — skip

        store = self.app.store  # type: ignore[attr-defined]
        store.clear_filter()
        store.apply_filter(predicate)
        self._active_filter = f"{direction}:{value}"
        self._clear_search()
        self._refresh_record_list()
        source_name = self.app.source_name  # type: ignore[attr-defined]
        self.app.sub_title = f"{source_name}  {len(store)} records — :{self._active_filter}"

    def _apply_search(self, pattern: str) -> None:
        """Apply text/regex search and store match indices."""
        from tav.query import search_records

        try:
            indices = search_records(self.app.store, pattern)  # type: ignore[attr-defined]
        except ValueError as e:
            self.app.notify(f"Invalid pattern: {e}", severity="error")
            return

        self._match_indices = indices
        self._match_cursor = 0 if indices else -1
        self._search_active = bool(indices)

        if not indices:
            self.app.notify("No matches found", severity="warning")
            return

        count = len(indices)
        self.app.notify(f"{count} match{'es' if count != 1 else ''}")
        self._jump_to_match()

    def _jump_to_match(self) -> None:
        """Move RecordList cursor to current match."""
        if self._match_cursor < 0 or not self._match_indices:
            return
        idx = self._match_indices[self._match_cursor]
        record_list = self.query_one(RecordList)
        record_list._cursor = idx
        record_list.scroll_to(y=idx, animate=False)
        record_list.refresh()

    def _clear_search(self) -> None:
        self._match_indices = []
        self._match_cursor = -1
        self._search_active = False

    def _refresh_record_list(self) -> None:
        """Update virtual size and refresh the record list after a store change."""
        record_list = self.query_one(RecordList)
        store = self.app.store  # type: ignore[attr-defined]
        record_list._cursor = 0
        record_list._max_content_width = record_list._compute_max_content_width()
        record_list.virtual_size = Size(
            max(record_list._max_content_width, record_list.size.width or 80),
            max(len(store), 1),
        )
        record_list.refresh()
