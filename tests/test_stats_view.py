# ABOUTME: Tests for _format_span in the stats view screen.
# ABOUTME: Covers all duration branches and pluralization edge cases.
import pytest

from tav.screens.stats_view import _format_span


@pytest.mark.parametrize("seconds, expected", [
    (0,       "< 1 minute"),
    (30,      "< 1 minute"),
    (59.9,    "< 1 minute"),
    (60,      "1 minute"),
    (120,     "2 minutes"),
    (3599,    "59 minutes"),
    (3600,    "1 hour"),
    (7200,    "2 hours"),
    (3660,    "1 hour 1 minute"),
    (3720,    "1 hour 2 minutes"),
    (7260,    "2 hours 1 minute"),
    (86400,   "1 day"),
    (172800,  "2 days"),
    (90000,   "1 day 1 hour"),
    (93600,   "1 day 2 hours"),
    (90060,   "1 day 1 hour"),   # 1d 1h 1m — minutes dropped at day scale
])
def test_format_span(seconds, expected):
    assert _format_span(seconds) == expected
