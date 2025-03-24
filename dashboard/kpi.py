"""
Helper class to load and render KPIs metrics into Streamlit UI
"""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import conf
import polars as pl
import streamlit as st
import yaml


@dataclass
class KPI:
    label: str
    key: str
    format: str = "{}"
    goal: Optional[float] = None
    is_time: bool = False


def load_kpi_config(
    yaml_path: Path = Path(__file__).parent / conf.kpi_config_filename,
) -> dict[str, list[KPI]]:
    with Path.open(yaml_path) as f:
        raw = yaml.safe_load(f)
    return {section: [KPI(**item) for item in items] for section, items in raw.items()}


def get_average(agg_df: pl.DataFrame, metric: str):
    """
    Safely extract the average value for a given metric from the aggregated DataFrame.

    Args:
        agg_df (pl.DataFrame): Aggregated DataFrame containing "metric_name" and "avg_quantity".
        metric (str): The metric name to extract.

    Returns:
        float | None: The average value if found, otherwise None.
    """
    df_metric = agg_df.filter(pl.col("metric_name") == metric)
    if df_metric.is_empty():
        return None
    return df_metric["avg_quantity"][0]


def render_kpis(section: str, values: dict[str, Any], config: dict[str, Any]) -> None:
    """
    Render a section of KPI metrics to the Streamlit UI.

    Args:
        section (str): The section name (e.g. "macros", "sleep") to pull config for.
        values (dict[str, Any]): Dictionary of computed KPI values keyed by metric name.
        config (dict[str, Any]): Loaded YAML config mapping sections to KPI definitions.

    This function looks up the metrics for the given section, formats each one according
    to the provided rules (e.g., formatting, delta, time display), and renders them as
    Streamlit metrics.
    """
    kpis = config.get(section, [])
    cols = st.columns(len(kpis))

    for col, kpi in zip(cols, kpis):
        key = kpi.key
        val = values.get(key)
        fmt = kpi.format
        is_time = kpi.is_time

        goal = kpi.goal
        delta = None
        if goal is not None and val is not None and not is_time:
            pct_change = (val - goal) / goal * 100
            delta = f"{pct_change:+.0f}%"

        if is_time and isinstance(val, datetime):
            val_str = val.strftime(fmt)
        elif val is not None:
            val_str = fmt.format(val)
        else:
            val_str = "N/A"

        col.metric(kpi.label, val_str, delta)


def render_kpi_section(
    section: str,
    df: pl.DataFrame,
    kpi_config: dict[str, Any],
    overrides: dict[str, Any] = dict(),
) -> None:
    """
    Compute averages for a KPI section, optionally override values, and render.

    Args:
        section (str): Section name from config (e.g. "macros", "sleep", "activity").
        df (pl.DataFrame): Filtered Polars DataFrame with metric_name and quantity.
        kpi_config (dict[str, Any]): KPI config loaded from YAML.
        overrides (dict[str, Any], optional): Manual override values by key.
    """
    overrides = overrides or {}

    avg_df = df.group_by("metric_name").agg(
        [pl.col("quantity").mean().alias("avg_quantity")]
    )
    keys = [k.key for k in kpi_config.get(section, [])]

    values = {
        key: overrides[key] if key in overrides else get_average(avg_df, key)
        for key in keys
    }

    render_kpis(section, values, kpi_config)
