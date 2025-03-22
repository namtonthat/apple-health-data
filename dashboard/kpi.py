"""
Helper class to load and render KPIs metrics into Streamlit UI
"""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import conf
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
    yaml_path: Path = Path(conf.kpi_config_path),
) -> dict[str, list[KPI]]:
    with Path.open(yaml_path) as f:
        raw = yaml.safe_load(f)
    return {section: [KPI(**item) for item in items] for section, items in raw.items()}


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
