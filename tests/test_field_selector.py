# ABOUTME: Tests for FieldSelector widget — flatten, toggle, select all/none, parent state.
# ABOUTME: Exercises pure logic functions without launching a full Textual app.
from tav.store import FieldTree
from tav.widgets.field_selector import _flatten, _check_state, _toggle


# ---------------------------------------------------------------------------
# _flatten
# ---------------------------------------------------------------------------


def test_flatten_single_level():
    tree: FieldTree = {"a": {}, "b": {}, "c": {}}
    items = _flatten(tree)
    assert items == [(("a",), 0), (("b",), 0), (("c",), 0)]


def test_flatten_nested():
    tree: FieldTree = {"user": {"name": {}, "age": {}}}
    items = _flatten(tree)
    assert items == [
        (("user",), 0),
        (("user", "age"), 1),
        (("user", "name"), 1),
    ]


def test_flatten_sorted_keys():
    tree: FieldTree = {"z": {}, "a": {}, "m": {}}
    items = _flatten(tree)
    paths = [p for p, _ in items]
    assert paths == [("a",), ("m",), ("z",)]


def test_flatten_preorder_dfs():
    """Pre-order: parent appears before children."""
    tree: FieldTree = {"b": {"x": {}}, "a": {}}
    items = _flatten(tree)
    paths = [p for p, _ in items]
    assert paths.index(("a",)) < paths.index(("b",))
    assert paths.index(("b",)) < paths.index(("b", "x"))


def test_flatten_depth():
    tree: FieldTree = {"top": {"mid": {"leaf": {}}}}
    items = _flatten(tree)
    assert items == [
        (("top",), 0),
        (("top", "mid"), 1),
        (("top", "mid", "leaf"), 2),
    ]


# ---------------------------------------------------------------------------
# _check_state
# ---------------------------------------------------------------------------


def test_check_state_all_selected():
    tree: FieldTree = {"a": {}, "b": {}}
    items = _flatten(tree)
    selected = {("a",), ("b",)}
    assert _check_state(("a",), items, selected) == "checked"
    assert _check_state(("b",), items, selected) == "checked"


def test_check_state_none_selected():
    tree: FieldTree = {"a": {}, "b": {}}
    items = _flatten(tree)
    selected: set = set()
    assert _check_state(("a",), items, selected) == "unchecked"


def test_check_state_parent_all_children_selected():
    tree: FieldTree = {"user": {"name": {}, "age": {}}}
    items = _flatten(tree)
    selected = {("user",), ("user", "name"), ("user", "age")}
    assert _check_state(("user",), items, selected) == "checked"


def test_check_state_parent_no_children_selected():
    tree: FieldTree = {"user": {"name": {}, "age": {}}}
    items = _flatten(tree)
    selected: set = set()
    assert _check_state(("user",), items, selected) == "unchecked"


def test_check_state_parent_partial():
    tree: FieldTree = {"user": {"name": {}, "age": {}}}
    items = _flatten(tree)
    selected = {("user", "name")}
    assert _check_state(("user",), items, selected) == "partial"


# ---------------------------------------------------------------------------
# _toggle
# ---------------------------------------------------------------------------


def test_toggle_on_adds_path_and_descendants():
    tree: FieldTree = {"user": {"name": {}, "age": {}}}
    items = _flatten(tree)
    selected: set = set()
    result = _toggle(("user",), items, selected)
    assert ("user",) in result
    assert ("user", "name") in result
    assert ("user", "age") in result


def test_toggle_off_removes_path_and_descendants():
    tree: FieldTree = {"user": {"name": {}, "age": {}}}
    items = _flatten(tree)
    selected = {("user",), ("user", "name"), ("user", "age")}
    result = _toggle(("user",), items, selected)
    assert ("user",) not in result
    assert ("user", "name") not in result
    assert ("user", "age") not in result


def test_toggle_leaf_on():
    tree: FieldTree = {"a": {}, "b": {}}
    items = _flatten(tree)
    selected: set = set()
    result = _toggle(("a",), items, selected)
    assert ("a",) in result
    assert ("b",) not in result


def test_toggle_leaf_off():
    tree: FieldTree = {"a": {}, "b": {}}
    items = _flatten(tree)
    selected = {("a",), ("b",)}
    result = _toggle(("a",), items, selected)
    assert ("a",) not in result
    assert ("b",) in result


# ---------------------------------------------------------------------------
# Initial selection from None (all selected)
# ---------------------------------------------------------------------------


def test_all_paths_from_none():
    """When current_selection is None, all paths should be pre-selected."""
    tree: FieldTree = {"a": {}, "b": {"c": {}}}
    items = _flatten(tree)
    all_paths = {p for p, _ in items}
    # All paths in flatten result should be the initial selection
    assert all_paths == {("a",), ("b",), ("b", "c")}
