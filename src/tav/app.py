# ABOUTME: Textual App subclass for tav — the TUI entry point.
# ABOUTME: Owns shared state (RecordStore, time_field, source_name) and screen registry.
from typing import Callable

from datetime import datetime
from textual.app import App

from tav.store import RecordStore
from tav.types import JsonValue
from tav.screens.data_view import DataViewScreen
from tav.time_parse import parse_timestamp


class TavApp(App):
    """Terminal time-series viewer application."""

    CSS = """
    TavApp {
        background: $background;
    }
    """

    def __init__(
        self,
        store: RecordStore,
        time_field: str | None = None,
        time_parser: Callable[[JsonValue], datetime | None] = parse_timestamp,
        source_name: str = "<stdin>",
        start_stats: bool = False,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.store = store
        self.time_field = time_field
        self.time_parser = time_parser
        self.source_name = source_name
        self.start_stats = start_stats

    def on_mount(self) -> None:
        self.push_screen(DataViewScreen())
        if self.start_stats:
            from tav.screens.stats_view import StatsViewScreen

            self.push_screen(StatsViewScreen())

    def action_quit(self) -> None:
        self.exit()
