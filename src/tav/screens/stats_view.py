# ABOUTME: StatsViewScreen — displays computed statistics for the loaded dataset
# ABOUTME: Shows time range, field completeness table, and value distributions.
from rich import box
from rich.table import Table
from rich.text import Text
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import VerticalScroll
from textual.screen import Screen
from textual.widgets import Footer, Header, Static

from tav.stats import DataStats


def _format_span(seconds: float) -> str:
    """Format a duration in seconds as a human-readable string."""
    if seconds < 60:
        return "< 1 minute"
    if seconds < 3600:
        minutes = int(seconds // 60)
        return f"{minutes} minute{'s' if minutes != 1 else ''}"
    if seconds < 86400:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        if minutes == 0:
            return f"{hours} hour{'s' if hours != 1 else ''}"
        return f"{hours} hour{'s' if hours != 1 else ''} {minutes} minute{'s' if minutes != 1 else ''}"
    days = int(seconds // 86400)
    hours = int((seconds % 86400) // 3600)
    if hours == 0:
        return f"{days} day{'s' if days != 1 else ''}"
    return f"{days} day{'s' if days != 1 else ''} {hours} hour{'s' if hours != 1 else ''}"


def _format_value_counts(value_counts: dict, top_n: int = 5) -> str:
    """Format top-N value counts as a compact inline string."""
    sorted_items = sorted(value_counts.items(), key=lambda x: x[1], reverse=True)[:top_n]
    return "  ".join(f"{k}: {v}" for k, v in sorted_items)


class StatsViewScreen(Screen):
    """Full-screen stats view showing dataset metrics."""

    BINDINGS = [
        Binding("s", "back_to_data", "Data view"),
        Binding("escape", "back_to_data", "Data view"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        with VerticalScroll(id="stats-container"):
            yield Static(id="overview-section")
            yield Static(id="time-section")
            yield Static(id="fields-section")
        yield Footer()

    def on_mount(self) -> None:
        """Compute stats and populate the view."""
        from tav.stats import compute_stats

        self.app.title = "tav — Stats"  # type: ignore[attr-defined]
        self.app.sub_title = ""  # type: ignore[attr-defined]

        data_stats = compute_stats(
            self.app.store,  # type: ignore[attr-defined]
            self.app.time_field,  # type: ignore[attr-defined]
            self.app.time_parser,  # type: ignore[attr-defined]
        )
        self._render_stats(data_stats)

    def _render_stats(self, data_stats: DataStats) -> None:
        """Populate the scrollable container with stats widgets."""
        self._render_overview(data_stats)
        self._render_time_stats(data_stats)
        self._render_field_stats(data_stats)

    def _render_overview(self, data_stats: DataStats) -> None:
        from tav.screens.data_view import DataViewScreen

        source_name = self.app.source_name  # type: ignore[attr-defined]
        active_filter: str | None = None
        for screen in reversed(self.app.screen_stack):  # type: ignore[attr-defined]
            if isinstance(screen, DataViewScreen):
                active_filter = screen.active_filter
                break

        lines = Text()
        lines.append("Dataset Overview\n", style="bold cyan")
        lines.append("────────────────\n", style="dim")
        lines.append("Source:     ", style="bold")
        lines.append(f"{source_name}\n")
        lines.append("Total:      ", style="bold")
        lines.append(
            f"{data_stats.total_count} records "
            f"({data_stats.object_count} objects, {data_stats.error_count} errors)\n"
        )

        if data_stats.filtered_count != data_stats.total_count:
            lines.append("Filtered:   ", style="bold")
            lines.append(f"{data_stats.filtered_count} records\n")

        if active_filter is not None:
            lines.append("Filter:     ", style="bold")
            lines.append(f"{active_filter}\n")

        self.query_one("#overview-section", Static).update(lines)

    def _render_time_stats(self, data_stats: DataStats) -> None:
        ts = data_stats.time_stats
        if ts is None:
            self.query_one("#time-section", Static).update("")
            return

        lines = Text()
        lines.append("\nTime Range\n", style="bold cyan")
        lines.append("──────────\n", style="dim")
        lines.append("Field:      ", style="bold")
        lines.append(f"{self.app.time_field}\n")  # type: ignore[attr-defined]
        lines.append("Earliest:   ", style="bold")
        lines.append(f"{ts.min_time}\n")
        lines.append("Latest:     ", style="bold")
        lines.append(f"{ts.max_time}\n")

        if ts.span_seconds is not None:
            lines.append("Span:       ", style="bold")
            lines.append(f"{_format_span(ts.span_seconds)}\n")

        self.query_one("#time-section", Static).update(lines)

    def _render_field_stats(self, data_stats: DataStats) -> None:
        if not data_stats.field_stats:
            self.query_one("#fields-section", Static).update("")
            return

        header = Text()
        header.append("\nField Statistics\n", style="bold cyan")
        header.append("────────────────\n", style="dim")

        table = Table(box=box.SIMPLE, show_header=True, header_style="bold cyan", padding=(0, 1))
        table.add_column("Field", style="bold")
        table.add_column("Type", style="dim")
        table.add_column("Present", justify="right")
        table.add_column("Cardinality")

        sorted_fields = sorted(
            data_stats.field_stats,
            key=lambda f: f.completeness,
            reverse=True,
        )

        for fs in sorted_fields:
            pct = f"{fs.completeness * 100:.0f}%"

            if fs.cardinality == "high":
                cardinality_str = f"high ({fs.unique_count} unique)"
            elif fs.cardinality == "medium":
                cardinality_str = f"medium ({fs.unique_count} unique)"
            else:
                cardinality_str = fs.cardinality

            table.add_row(fs.name, fs.value_type, pct, cardinality_str)

            if fs.value_counts and fs.cardinality in ("low", "medium"):
                value_line = "  \u2514\u2500 " + _format_value_counts(fs.value_counts)
                table.add_row(
                    Text(value_line, style="dim"),
                    "",
                    "",
                    "",
                )

        from rich.console import Group
        renderable = Group(header, table)
        self.query_one("#fields-section", Static).update(renderable)

    def action_back_to_data(self) -> None:
        self.app.pop_screen()
