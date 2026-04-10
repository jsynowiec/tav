# ABOUTME: CommandBar — dual-mode input bar for command and search entry.
# ABOUTME: ':' activates command mode (JMESPath filter); '/' activates search mode.
from textual import events
from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.message import Message
from textual.widget import Widget
from textual.widgets import Input, Label


class CommandBar(Widget):
    DEFAULT_CSS = """
    CommandBar {
        height: 1;
        display: none;
        dock: bottom;
    }
    CommandBar Horizontal {
        height: 1;
    }
    CommandBar Label {
        width: 2;
        padding: 0;
        color: $accent;
        text-style: bold;
    }
    CommandBar Input {
        width: 1fr;
        height: 1;
        border: none;
        padding: 0 1;
        background: $surface;
        color: $text;
    }
    CommandBar Input:focus {
        border: none;
    }
    """

    class CommandSubmitted(Message):
        """User submitted a command-mode expression."""

        def __init__(self, expression: str) -> None:
            super().__init__()
            self.expression = expression

    class SearchSubmitted(Message):
        """User submitted a search-mode pattern."""

        def __init__(self, pattern: str) -> None:
            super().__init__()
            self.pattern = pattern

    class Dismissed(Message):
        """User dismissed the bar with Escape."""

        pass

    _MODE_COMMAND = "command"
    _MODE_SEARCH = "search"

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._mode = self._MODE_COMMAND

    def compose(self) -> ComposeResult:
        with Horizontal():
            yield Label(":", id="mode-prefix")
            yield Input(placeholder="", id="bar-input")

    def activate_command(self) -> None:
        """Show bar in command mode with ':' prefix."""
        self._mode = self._MODE_COMMAND
        self.query_one("#mode-prefix", Label).update(":")
        inp = self.query_one("#bar-input", Input)
        inp.placeholder = "JMESPath filter, e.g.: sensor_id == 'value'"
        inp.value = ""
        self.display = True
        self.call_after_refresh(inp.focus)

    def activate_search(self) -> None:
        """Show bar in search mode with '/' prefix."""
        self._mode = self._MODE_SEARCH
        self.query_one("#mode-prefix", Label).update("/")
        inp = self.query_one("#bar-input", Input)
        inp.placeholder = "Regex pattern, e.g.: error|warning"
        inp.value = ""
        self.display = True
        self.call_after_refresh(inp.focus)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        value = event.value.strip()
        self.display = False
        if value:
            if self._mode == self._MODE_COMMAND:
                self.post_message(self.CommandSubmitted(value))
            else:
                self.post_message(self.SearchSubmitted(value))

    def on_key(self, event: events.Key) -> None:
        if event.key == "escape":
            self.display = False
            self.post_message(self.Dismissed())
            event.stop()
