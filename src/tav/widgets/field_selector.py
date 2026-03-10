# ABOUTME: FieldSelector — modal overlay for toggling individual fields on/off in the record list.
# ABOUTME: Returns the selected field path set, or None if cancelled.
from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Label, ListItem, ListView, Static

from tav.store import FieldTree


# ---------------------------------------------------------------------------
# Pure helpers (tested independently)
# ---------------------------------------------------------------------------

def _flatten(tree: FieldTree) -> list[tuple[tuple[str, ...], int]]:
    """Return a pre-order DFS list of (path_tuple, depth) pairs, sorted by key at each level."""
    result: list[tuple[tuple[str, ...], int]] = []

    def _walk(subtree: FieldTree, prefix: tuple[str, ...], depth: int) -> None:
        for key in sorted(subtree):
            path = prefix + (key,)
            result.append((path, depth))
            if subtree[key]:
                _walk(subtree[key], path, depth + 1)

    _walk(tree, (), 0)
    return result


def _check_state(
    path: tuple[str, ...],
    items: list[tuple[tuple[str, ...], int]],
    selected: set[tuple[str, ...]],
) -> str:
    """Return 'checked', 'unchecked', or 'partial' for path based on selected set."""
    # Collect path itself and all descendant paths
    family = [p for p, _ in items if p == path or (len(p) > len(path) and p[: len(path)] == path)]
    if not family:
        return "unchecked"
    selected_count = sum(1 for p in family if p in selected)
    if selected_count == len(family):
        return "checked"
    if selected_count == 0:
        return "unchecked"
    return "partial"


def _toggle(
    path: tuple[str, ...],
    items: list[tuple[tuple[str, ...], int]],
    selected: set[tuple[str, ...]],
) -> set[tuple[str, ...]]:
    """Toggle path and all descendants. Returns a new set."""
    family = [p for p, _ in items if p == path or (len(p) > len(path) and p[: len(path)] == path)]
    result = set(selected)
    if path in result:
        # Toggle OFF: remove path and all descendants
        result -= set(family)
    else:
        # Toggle ON: add path and all descendants
        result |= set(family)
    return result


# ---------------------------------------------------------------------------
# FieldSelector widget
# ---------------------------------------------------------------------------

_CHECKBOX = {"checked": "[X]", "unchecked": "[ ]", "partial": "[-]"}


class FieldSelector(ModalScreen[set[tuple[str, ...]] | None]):
    """Field selector overlay. Returns the selected field set or None if cancelled."""

    BINDINGS = [
        Binding("space", "toggle_item", "Toggle", show=False),
        Binding("a", "select_all", "All"),
        Binding("x", "select_none", "None"),
        Binding("enter", "apply", "Apply"),
        Binding("escape", "cancel", "Cancel"),
    ]

    DEFAULT_CSS = """
    FieldSelector {
        align: center middle;
    }
    FieldSelector > #container {
        width: 60;
        height: auto;
        max-height: 24;
        border: round $primary;
        background: $surface;
        padding: 1 2;
    }
    FieldSelector #hints-top {
        height: auto;
        margin-bottom: 1;
    }
    FieldSelector ListView {
        height: auto;
        max-height: 16;
    }
    FieldSelector #hints-bottom {
        height: auto;
        margin-top: 1;
    }
    """

    def __init__(
        self,
        tree: FieldTree,
        current_selection: set[tuple[str, ...]] | None,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self._tree = tree
        self._items = _flatten(tree)
        if current_selection is None:
            self._selected = {p for p, _ in self._items}
        else:
            self._selected = set(current_selection)

    def compose(self) -> ComposeResult:
        with Vertical(id="container"):
            yield Static("[a] Select all   [x] Select none", id="hints-top")
            yield ListView(*self._build_list_items(), id="field-list")
            yield Static("Enter: apply  Escape: cancel", id="hints-bottom")

    def _build_list_items(self) -> list[ListItem]:
        items = []
        for path, depth in self._items:
            state = _check_state(path, self._items, self._selected)
            checkbox = _CHECKBOX[state]
            indent = "  " * depth
            label = f"{indent}{checkbox} {path[-1]}"
            items.append(ListItem(Label(label)))
        return items

    def _rebuild_list(self) -> None:
        list_view = self.query_one("#field-list", ListView)
        list_view.clear()
        for item in self._build_list_items():
            list_view.append(item)

    def action_toggle_item(self) -> None:
        list_view = self.query_one("#field-list", ListView)
        idx = list_view.index
        if idx is None or idx >= len(self._items):
            return
        path, _ = self._items[idx]
        self._selected = _toggle(path, self._items, self._selected)
        self._rebuild_list()

    def action_select_all(self) -> None:
        self._selected = {p for p, _ in self._items}
        self._rebuild_list()

    def action_select_none(self) -> None:
        self._selected = set()
        self._rebuild_list()

    def action_apply(self) -> None:
        self.dismiss(self._selected)

    def action_cancel(self) -> None:
        self.dismiss(None)
