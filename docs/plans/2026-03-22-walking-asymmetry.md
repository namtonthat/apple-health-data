# Walking Asymmetry in Daily Summary Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add walking asymmetry percentage to `fct_daily_summary` and display it in the Recovery page's Daily Breakdown table, color-coded for injury risk (green ≤5%, orange 5–10%, red >10%).

**Architecture:** `walking_asymmetry_pct` already exists in `int_health__daily_activity` but is NOT included in `fct_daily_summary`. We need to: (1) add it to the summary model, (2) rebuild dbt, (3) add it to the breakdown table UI.

**Tech Stack:** dbt/DuckDB (SQL), Streamlit, Polars

---

### Task 1: Add walking_asymmetry_pct to fct_daily_summary

**Files:**
- Modify: `dbt_project/models/marts/fct_daily_summary.sql:58-67`

**Step 1: Add the column**

In `fct_daily_summary.sql`, in the `final` CTE after `a.meditation_minutes,` (line 67), add:

```sql
        round(a.walking_asymmetry_pct, 1) as walking_asymmetry_pct,
```

**Step 2: Rebuild dbt**

Run: `set -a && source .env && set +a && cd dbt_project && uv run dbt run --profiles-dir . --select fct_daily_summary recent_fct_daily_summary`

**Step 3: Verify the column exists**

Run: `set -a && source .env && set +a && uv run python -c "import os, duckdb; conn = duckdb.connect(':memory:'); conn.execute(f\"SET s3_region='ap-southeast-2'\"); conn.execute(f\"SET s3_access_key_id='{os.environ['AWS_ACCESS_KEY_ID']}'\"); conn.execute(f\"SET s3_secret_access_key='{os.environ['AWS_SECRET_ACCESS_KEY']}'\"); print(conn.execute(\"SELECT date, walking_asymmetry_pct FROM read_parquet('s3://api-health-data-ntonthat/transformed/recent/fct_daily_summary') WHERE walking_asymmetry_pct IS NOT NULL ORDER BY date DESC LIMIT 5\").fetchdf())"`

**Step 4: Commit dbt change**

```bash
git add dbt_project/models/marts/fct_daily_summary.sql
git commit -m "feat: add walking_asymmetry_pct to fct_daily_summary"
```

---

### Task 2: Add walking asymmetry to the Daily Breakdown table

**Files:**
- Modify: `src/dashboard/pages/1_Recovery.py`

**Step 1: Add to breakdown_cols dict** (around line 40-51)

Add after the `"weight_kg"` entry:
```python
        "walking_asymmetry_pct": "walking_asymmetry_pct" in df_daily.columns,
```

**Step 2: Add to col_map** (around line 120-121)

Add after the `"Weight"` entry:
```python
    if "walking_asymmetry_pct" in avail_cols:
        col_map["walking_asymmetry_pct"] = "Asym %"
```

**Step 3: Add asymmetry-specific color logic**

Asymmetry uses inverted thresholds (lower is better): ≤5% green, 5–10% orange, >10% red.

Add to the `binary_goals` section (around line 141-143):
```python
    # Asymmetry goals (lower is better: ≤5% green, 5-10% orange, >10% red)
    asymmetry_cols = set()
    if "Asym %" in display_df.columns:
        asymmetry_cols.add("Asym %")
```

Update `_color_cell` to handle asymmetry:
```python
    def _color_cell(val, col_name):
        if pd.isna(val):
            return ""
        if col_name in graduated_goals and graduated_goals[col_name] is not None:
            color = goal_status_color(float(val), graduated_goals[col_name])
            return f"background-color: {color}33; color: {color}"
        if col_name in binary_goals and binary_goals[col_name] is not None:
            color = "#00CC96" if float(val) >= binary_goals[col_name] else "#EF553B"
            return f"background-color: {color}33; color: {color}"
        if col_name in asymmetry_cols:
            v = float(val)
            if v <= 5:
                color = "#00CC96"
            elif v <= 10:
                color = "#FFA500"
            else:
                color = "#EF553B"
            return f"background-color: {color}33; color: {color}"
        return ""
```

**Step 4: Add formatting**

Add to the format dict:
```python
"Asym %": "{:.1f}%",
```

**Step 5: Update legend**

Add to the `bd_legend` caption:
```python
"**Asym %** — walking asymmetry (green ≤5%, orange 5–10%, red >10%)  \n"
```

**Step 6: Run lint**

Run: `uv run ruff check --fix src/dashboard/pages/1_Recovery.py && uv run ruff format src/dashboard/pages/1_Recovery.py`

**Step 7: Commit**

```bash
git add src/dashboard/pages/1_Recovery.py
git commit -m "feat: add walking asymmetry to Recovery daily breakdown"
```
