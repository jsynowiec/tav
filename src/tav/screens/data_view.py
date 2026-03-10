# ABOUTME: Main data view screen — shows JSONL records in a scrollable list.
# ABOUTME: Composes Header, RecordList, and Footer with keybinding hints.
from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Footer, Header

from tav.widgets.record_list import RecordList


class DataViewScreen(Screen):
    """Primary screen showing the record list."""

    BINDINGS = [
        ("q", "app.quit", "Quit"),
    ]

    def compose(self) -> ComposeResult:
        store = self.app.store  # type: ignore[attr-defined]
        source_name = self.app.source_name  # type: ignore[attr-defined]
        record_count = len(store)
        yield Header(show_clock=False)
        yield RecordList(store)
        yield Footer()

    def on_mount(self) -> None:
        store = self.app.store  # type: ignore[attr-defined]
        source_name = self.app.source_name  # type: ignore[attr-defined]
        self.app.title = "tav"
        self.app.sub_title = f"{source_name}  {len(store)} records"
