# ABOUTME: Tests for FieldNav overlay widget.
# ABOUTME: Covers on_input_submitted dismiss behavior with and without filter matches.
import pytest
from unittest.mock import MagicMock

from tav.widgets.field_nav import FieldNav


def _make_field_nav(fields):
    """Return a FieldNav stub with a mocked dismiss method."""
    nav = object.__new__(FieldNav)
    nav._all_fields = sorted(fields)
    nav._filtered = list(nav._all_fields)
    nav.dismiss = MagicMock()
    return nav


def test_input_submitted_dismisses_first_filtered_field():
    """When filtered list is non-empty, dismiss is called with the first match."""
    nav = _make_field_nav(["alpha", "beta", "gamma"])
    nav._filtered = ["beta", "gamma"]
    nav.on_input_submitted(MagicMock())
    nav.dismiss.assert_called_once_with("beta")


def test_input_submitted_with_no_matches_dismisses_none():
    """When no fields match the filter, dismiss is called with None."""
    nav = _make_field_nav(["alpha"])
    nav._filtered = []
    nav.on_input_submitted(MagicMock())
    nav.dismiss.assert_called_once_with(None)


@pytest.mark.parametrize(
    "fields, filtered, expected",
    [
        (["x", "y", "z"], ["x", "y", "z"], "x"),
        (["z", "a", "m"], ["a"], "a"),
    ],
)
def test_input_submitted_always_returns_first_in_filtered_list(
    fields, filtered, expected
):
    """dismiss receives the first element of _filtered regardless of original order."""
    nav = _make_field_nav(fields)
    nav._filtered = filtered
    nav.on_input_submitted(MagicMock())
    nav.dismiss.assert_called_once_with(expected)
