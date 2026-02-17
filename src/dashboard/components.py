"""Shared UI components for the dashboard."""

from __future__ import annotations

import math
from datetime import date, timedelta

import streamlit as st

from dashboard.config import today_local


def metric_with_goal(
    label: str,
    value: float | None,
    goal: float | None = None,
    unit: str = "",
    fmt: str = ".1f",
    inverse: bool = False,
    ref_label: str = "goal",
) -> None:
    """Display a metric with optional goal/reference delta chip.

    Args:
        label: Metric label.
        value: Current value.
        goal: Target or reference value (if None, no delta shown).
        unit: Unit suffix (e.g., "h", "g").
        fmt: Format string for numbers.
        inverse: If True, lower is better (delta color inverted).
        ref_label: Label for the reference value (e.g., "goal", "60d ago").
    """
    if value is None:
        st.metric(label, "-")
        return

    display_value = f"{value:{fmt}}{unit}"

    if goal is not None:
        delta = value - goal
        delta_str = f"{delta:+{fmt}}{unit} vs {goal:{fmt}}{unit} {ref_label}"
        delta_color = "inverse" if inverse else "normal"
        st.metric(label, display_value, delta=delta_str, delta_color=delta_color)
    else:
        st.metric(label, display_value)


def goal_status_color(value: float, goal: float, tolerance: float = 0.10) -> str:
    """Return hex color based on proximity to goal.

    Green: at goal. Yellow: within ±tolerance. Red: outside tolerance.
    Bounds are floored/ceiled for clean integer thresholds.
    """
    lower = math.floor(goal * (1 - tolerance))
    upper = math.ceil(goal * (1 + tolerance))

    if round(value) == round(goal):
        return "#00CC96"  # green — at goal
    elif lower <= value <= upper:
        return "#FFA500"  # amber — within tolerance
    else:
        return "#EF553B"  # red — outside tolerance


def metric_with_goal_color(
    label: str,
    value: float | None,
    goal: float | None = None,
    unit: str = "",
    fmt: str = ".0f",
    tolerance: float = 0.10,
) -> None:
    """Display a metric with tri-color goal status (green/amber/red).

    Args:
        label: Metric label.
        value: Current value.
        goal: Target value.
        unit: Unit suffix (e.g., "g", "kcal").
        fmt: Format string for numbers.
        tolerance: Fraction (0–1) for the yellow band around the goal.
    """
    if value is None:
        st.metric(label, "-")
        return

    display_value = f"{value:{fmt}}{unit}"

    if goal is None or goal == 0:
        st.metric(label, display_value)
        return

    delta = value - goal
    color = goal_status_color(value, goal, tolerance)
    delta_str = f"{delta:+{fmt}}{unit} vs {goal:{fmt}}{unit} goal"

    st.markdown(
        f"<div>"
        f'<p style="font-size:0.82rem;opacity:0.6;margin:0 0 -0.1rem 0;">{label}</p>'
        f'<p style="font-size:1.75rem;font-weight:700;margin:0;'
        f'padding:0.2rem 0;">{display_value}</p>'
        f'<p style="font-size:0.82rem;color:{color};margin:0;">{delta_str}</p>'
        f"</div>",
        unsafe_allow_html=True,
    )


def vertical_divider(height: int = 100) -> None:
    """Render a vertical divider line."""
    st.markdown(
        f"<div style='border-left: 2px solid #444; height: {height}px; margin: 0 auto;'></div>",
        unsafe_allow_html=True,
    )


def date_filter_sidebar(
    presets: list[str] | None = None,
    max_lookback: int | None = None,
) -> tuple[date, date]:
    """Render date range sidebar with presets.

    Args:
        presets: List of preset labels. Defaults to common set.
        max_lookback: If set, constrains the custom date picker minimum.

    Returns:
        (start_date, end_date) tuple.
    """
    if presets is None:
        presets = ["Last 7 days", "Last 30 days", "This month", "Custom"]

    st.sidebar.title("Filters")

    preset = st.sidebar.radio("Date Range", presets, index=0)

    today = today_local()
    yesterday = today - timedelta(days=1)

    preset_days = {
        "Last 7 days": 7,
        "Last 14 days": 14,
        "Last 30 days": 30,
        "Last 90 days": 90,
    }

    if preset in preset_days:
        start_date = today - timedelta(days=preset_days[preset])
        end_date = yesterday
    elif preset == "This month":
        start_date = today.replace(day=1)
        end_date = yesterday
    else:
        # Custom
        kwargs = {}
        if max_lookback:
            kwargs["min_value"] = today - timedelta(days=max_lookback)
        start_date = st.sidebar.date_input(
            "Start date",
            today - timedelta(days=7),
            **kwargs,
        )
        end_date = st.sidebar.date_input("End date", yesterday)

    st.sidebar.markdown(f"**Showing:** {start_date} to {end_date}")
    return start_date, end_date
