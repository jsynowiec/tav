# ABOUTME: HelpOverlay — centered modal showing keybindings and command reference
# ABOUTME: Triggered by '?' key; dismissed by '?', Escape, or Enter.
from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import ModalScreen
from textual.widgets import Static

HELP_TEXT = """\
[bold]tav — Time-Series Viewer[/bold]

[bold]Navigation[/bold]
  [cyan]j / ↓[/cyan]      Move down
  [cyan]k / ↑[/cyan]      Move up
  [cyan]Home[/cyan]       Jump to top
  [cyan]End[/cyan]        Jump to bottom

[bold]Display[/bold]
  [cyan]Enter[/cyan]      Expand/collapse record detail
  [cyan]t[/cyan]          Toggle compact / pretty mode
  [cyan]a[/cyan]          Toggle objects-only / all-lines mode
  [cyan]o[/cyan]          Sort by time / restore file order
  [cyan]g[/cyan]          Go-to-field navigator

[bold]Search & Filter[/bold]
  [cyan]/[/cyan]          Search mode (text / regex)
  [cyan]:[/cyan]          Command mode (JMESPath filter, time range)
  [cyan]n / N[/cyan]      Next / previous match

[bold]General[/bold]
  [cyan]s[/cyan]          Toggle stats view
  [cyan]?[/cyan]          Show / hide this help
  [cyan]q[/cyan]          Quit
  [cyan]Escape[/cyan]     Close overlay / clear filter

[bold]Command examples[/bold]
  [cyan]:field == 'value'[/cyan]    Filter by field value
  [cyan]:field > 100[/cyan]         Filter by numeric comparison

              Press [cyan]?[/cyan] or [cyan]Escape[/cyan] to close\
"""


class HelpOverlay(ModalScreen):
    """Centered help overlay showing all keybindings and command syntax."""

    BINDINGS = [
        Binding("escape", "dismiss", "Close"),
        Binding("question_mark", "dismiss", "Close"),
        Binding("enter", "dismiss", "Close"),
    ]

    DEFAULT_CSS = """
    HelpOverlay {
        align: center middle;
    }
    HelpOverlay > Static {
        width: auto;
        height: auto;
        max-width: 70;
        border: round $primary;
        padding: 1 2;
        background: $surface;
    }
    """

    def compose(self) -> ComposeResult:
        yield Static(HELP_TEXT)

    def action_dismiss(self) -> None:
        self.dismiss()
