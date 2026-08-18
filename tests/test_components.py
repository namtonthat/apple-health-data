from __future__ import annotations

from datetime import date, datetime

import polars as pl

from dashboard.components import goal_status_color, style_goal_column
from dashboard.data import filter_date_range

GREEN = "#00CC96"
ORANGE = "#FFA500"
RED = "#EF553B"


def _cell(color: str) -> str:
    return f"background-color: {color}33; color: {color}"


class TestGoalStatusColorOneSided:
    """Default (floor goals): only shortfall is penalised; exceeding is green."""

    def test_above_goal_is_green(self):
        assert goal_status_color(8.8, 7.0) == GREEN

    def test_far_above_goal_is_still_green(self):
        assert goal_status_color(14.0, 7.0) == GREEN

    def test_within_10pct_below_is_green(self):
        assert goal_status_color(6.5, 7.0) == GREEN

    def test_10_to_20pct_below_is_orange(self):
        assert goal_status_color(6.0, 7.0) == ORANGE

    def test_more_than_20pct_below_is_red(self):
        assert goal_status_color(5.0, 7.0) == RED


class TestGoalStatusColorTwoSided:
    """Target goals (e.g. calories): overshooting is penalised too."""

    def test_far_above_goal_is_red(self):
        assert goal_status_color(8.8, 7.0, two_sided=True) == RED

    def test_slightly_above_goal_is_green(self):
        assert goal_status_color(7.5, 7.0, two_sided=True) == GREEN

    def test_15pct_above_goal_is_orange(self):
        assert goal_status_color(8.05, 7.0, two_sided=True) == ORANGE

    def test_more_than_20pct_below_is_red(self):
        assert goal_status_color(5.0, 7.0, two_sided=True) == RED

    def test_zero_goal_is_green(self):
        assert goal_status_color(5.0, 0.0, two_sided=True) == GREEN


class TestStyleGoalColumn:
    """Cell CSS shared by the Recovery daily-breakdown and Nutrition tables."""

    def test_none_value_is_blank(self):
        assert style_goal_column(None, 7.0) == ""

    def test_nan_value_is_blank(self):
        assert style_goal_column(float("nan"), 7.0) == ""

    def test_none_goal_is_blank(self):
        assert style_goal_column(8.0, None) == ""

    def test_default_matches_goal_status_color(self):
        assert style_goal_column(6.0, 7.0) == _cell(goal_status_color(6.0, 7.0))

    def test_two_sided_matches_goal_status_color(self):
        assert style_goal_column(8.8, 7.0, two_sided=True) == _cell(
            goal_status_color(8.8, 7.0, two_sided=True)
        )

    def test_inverse_at_goal_is_green(self):
        assert style_goal_column(55.0, 55.0, inverse=True) == _cell(GREEN)

    def test_inverse_below_goal_is_green(self):
        """Inverse (lower-is-better) goals are green at any undershoot, unlike graduated goals."""
        assert style_goal_column(40.0, 55.0, inverse=True) == _cell(GREEN)

    def test_inverse_slightly_over_goal_is_orange(self):
        assert style_goal_column(58.0, 55.0, inverse=True) == _cell(ORANGE)  # ~5.5% over

    def test_inverse_far_over_goal_is_red(self):
        assert style_goal_column(70.0, 55.0, inverse=True) == _cell(RED)  # ~27% over

    def test_inverse_zero_goal_is_green(self):
        assert style_goal_column(10.0, 0.0, inverse=True) == _cell(GREEN)


class TestFilterDateRange:
    """Shared date-range filter helper (previously copy-pasted across 3 pages)."""

    def test_filters_inclusive_range(self):
        df = pl.DataFrame(
            {
                "date": [date(2026, 1, 1), date(2026, 1, 5), date(2026, 1, 10)],
                "value": [1, 2, 3],
            }
        )
        result = filter_date_range(df, "date", date(2026, 1, 1), date(2026, 1, 5))
        assert result["value"].to_list() == [1, 2]

    def test_excludes_rows_outside_range(self):
        df = pl.DataFrame(
            {
                "date": [date(2026, 1, 1), date(2026, 1, 15)],
                "value": [1, 2],
            }
        )
        result = filter_date_range(df, "date", date(2026, 1, 5), date(2026, 1, 10))
        assert result.height == 0

    def test_empty_frame_is_returned_unchanged(self):
        df = pl.DataFrame()
        result = filter_date_range(df, "date", date(2026, 1, 1), date(2026, 1, 5))
        assert result.height == 0

    def test_missing_date_column_is_returned_unchanged(self):
        df = pl.DataFrame({"value": [1, 2, 3]})
        result = filter_date_range(df, "date", date(2026, 1, 1), date(2026, 1, 5))
        assert result.to_dict(as_series=False) == df.to_dict(as_series=False)

    def test_casts_non_date_column_before_comparing(self):
        df = pl.DataFrame(
            {
                "workout_date": [
                    datetime(2026, 1, 1, 9, 0),
                    datetime(2026, 1, 5, 10, 0),
                    datetime(2026, 1, 10, 8, 0),
                ],
                "value": [1, 2, 3],
            }
        )
        result = filter_date_range(df, "workout_date", date(2026, 1, 1), date(2026, 1, 5))
        assert result["value"].to_list() == [1, 2]
