# ABOUTME: RecordDetail — modal overlay for pretty-printing a single JSONL record.
# ABOUTME: Shown when the user presses Enter on a record; dismissed with Escape or Enter.
from __future__ import annotations

import json

from rich.json import JSON
from rich.text import Text
from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import ModalScreen
from textual.widgets import Static

from tav.loader import KIND_ARRAY, KIND_ERROR, KIND_OBJECT, ParsedLine

_MAX_WIDTH = 120


class RecordDetail(ModalScreen):
    """Modal overlay showing a single JSONL record pretty-printed."""

    DEFAULT_CSS = """
    RecordDetail {
        align: center middle;
    }

    RecordDetail > Static {
        width: auto;
        max-width: 120;
        height: auto;
        max-height: 80vh;
        border: round $primary;
        padding: 1 2;
        background: $surface;
        overflow-y: auto;
    }
    """

    BINDINGS = [
        Binding("escape", "dismiss", "Close", show=False),
        Binding("enter", "dismiss", "Close", show=False),
    ]

    def __init__(self, record: ParsedLine, **kwargs) -> None:
        super().__init__(**kwargs)
        self._record = record

    def compose(self) -> ComposeResult:
        record = self._record
        title = f"Record #{record.line_number}"

        if record.kind in (KIND_OBJECT, KIND_ARRAY):
            pretty = json.dumps(record.value, indent=2)
            content = JSON(pretty)
            yield Static(content, markup=False)
        elif record.kind == KIND_ERROR:
            text = Text(str(record.value), style="bold red")
            yield Static(text, markup=False)
        else:  # KIND_PRIMITIVE
            text = Text(str(record.value))
            yield Static(text, markup=False)

        # Set border title after compose via on_mount
        self._title = title

    def on_mount(self) -> None:
        self.query_one(Static).border_title = self._title
