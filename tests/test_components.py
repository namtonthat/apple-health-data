from __future__ import annotations

from dashboard.components import goal_status_color

GREEN = "#00CC96"
ORANGE = "#FFA500"
RED = "#EF553B"


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
