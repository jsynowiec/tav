# ABOUTME: FieldNav — overlay for navigating to a specific field in the record list
# ABOUTME: Shows all unique fields; user types to filter, Enter selects first match.
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Input, Label, ListItem, ListView


class FieldNav(ModalScreen[str | None]):
    """Field navigator overlay. Returns the selected field name or None."""

    BINDINGS = [
        Binding("escape", "dismiss_none", "Close"),
    ]

    DEFAULT_CSS = """
    FieldNav {
        align: center middle;
    }
    FieldNav > #container {
        width: 50;
        height: 20;
        border: round $primary;
        background: $surface;
        padding: 1;
    }
    FieldNav Input {
        width: 1fr;
        margin-bottom: 1;
    }
    FieldNav ListView {
        height: 1fr;
    }
    """

    def __init__(self, fields: list[str], **kwargs) -> None:
        super().__init__(**kwargs)
        self._all_fields = sorted(fields)
        self._filtered = list(self._all_fields)

    def compose(self) -> ComposeResult:
        with Vertical(id="container"):
            yield Label("Go to field:")
            yield Input(placeholder="Type to filter...", id="filter-input")
            yield ListView(
                *[ListItem(Label(f)) for f in self._all_fields],
                id="field-list",
            )

    def on_input_changed(self, event: Input.Changed) -> None:
        query = event.value.lower()
        list_view = self.query_one("#field-list", ListView)
        list_view.clear()
        self._filtered = [f for f in self._all_fields if query in f.lower()]
        for f in self._filtered:
            list_view.append(ListItem(Label(f)))

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if self._filtered:
            self.dismiss(self._filtered[0])
        else:
            self.dismiss(None)

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        label = event.item.query_one(Label)
        self.dismiss(str(label.renderable))

    def action_dismiss_none(self) -> None:
        self.dismiss(None)
