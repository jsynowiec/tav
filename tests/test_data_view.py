# ABOUTME: Tests for _apply_command behavior in the data view screen.
# ABOUTME: Covers store/UI consistency and subtitle format on filter operations.
from unittest.mock import MagicMock, PropertyMock, patch

import pytest

from tests.conftest import make_object
from tav.screens.data_view import DataViewScreen
from tav.store import RecordStore


def _make_screen(store):
    """Return a DataViewScreen stub with a mocked app and real store."""
    screen = object.__new__(DataViewScreen)
    screen._active_filter = None
    screen._match_indices = []
    screen._match_cursor = -1
    screen._search_active = False
    screen._overlay_visible = False
    screen._refresh_record_list = MagicMock()
    screen._clear_search = MagicMock()

    mock_app = MagicMock()
    mock_app.store = store
    mock_app.source_name = "test.jsonl"
    return screen, mock_app


def test_invalid_filter_after_valid_filter_clears_store():
    """Applying an invalid filter after a valid one must leave the store unfiltered."""
    lines = [make_object(i + 1, {"v": i}) for i in range(3)]
    store = RecordStore(lines)
    screen, mock_app = _make_screen(store)

    with patch.object(DataViewScreen, "app", new_callable=PropertyMock, return_value=mock_app):
        # Apply a valid filter first — store shrinks to 1 record
        screen._apply_command("v == `0`")
        assert len(store) == 1
        assert screen._active_filter is not None

        # Now apply an invalid JMESPath expression
        screen._apply_command("[?invalid[[[")

        # Store must show all records — filter was cleared, not silently lost
        assert len(store) == 3
        # _active_filter must be None — not the stale old expression
        assert screen._active_filter is None


@pytest.mark.parametrize("expression, expected_count", [
    ("v == `0`", 1),
    ("v > `0`", 2),
])
def test_subtitle_includes_active_filter_expression(expression, expected_count):
    """Subtitle must show source, filtered record count, and the filter expression."""
    lines = [make_object(i + 1, {"v": i}) for i in range(3)]
    store = RecordStore(lines)
    screen, mock_app = _make_screen(store)

    with patch.object(DataViewScreen, "app", new_callable=PropertyMock, return_value=mock_app):
        screen._apply_command(expression)

    expected_subtitle = f"test.jsonl  {expected_count} records — :{expression}"
    assert mock_app.sub_title == expected_subtitle


def test_time_filter_works_across_formats():
    """Time filter matches records regardless of timestamp format (epoch, ISO, strptime)."""
    lines = [
        make_object(1, {"ts": "2024-01-01T00:00:00Z"}),       # aware ISO
        make_object(2, {"ts": "2024-01-03T00:00:00"}),         # naive ISO
        make_object(3, {"ts": 1704240000}),                     # epoch (2024-01-03 00:00:00 UTC)
        make_object(4, {"ts": "2024-01-05 00:00:00"}),          # strptime
    ]
    store = RecordStore(lines)
    screen, mock_app = _make_screen(store)
    mock_app.time_field = "ts"

    with patch.object(DataViewScreen, "app", new_callable=PropertyMock, return_value=mock_app):
        screen._apply_time_filter("2024-01-02", "after")

    assert len(store) == 3
    line_nums = {store[i].line_number for i in range(len(store))}
    assert line_nums == {2, 3, 4}
