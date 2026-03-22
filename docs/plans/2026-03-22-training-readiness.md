# Training Readiness Score Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Create a computed "Training Readiness" score (0–100) as a dbt model, combining HRV, RHR, sleep hours, and deep sleep ratio. Display it as a prominent card + trend on the Recovery page.

**Architecture:** New dbt mart model `fct_training_readiness` that reads from `fct_daily_summary` and computes a composite score. Each component is normalized to 0–25 points and summed. The dashboard reads this via a new `load_training_readiness()` function.

**Tech Stack:** dbt/DuckDB (SQL), Streamlit, Altair, Polars

---

### Task 1: Create the dbt model

**Files:**
- Create: `dbt_project/models/marts/fct_training_readiness.sql`
- Modify: `dbt_project/models/marts/schema.yml`

**Step 1: Write the dbt model**

Create `dbt_project/models/marts/fct_training_readiness.sql`:

```sql
{{
  config(
    materialized='external',
    location='s3://{{ var("s3_bucket") }}/transformed/fct_training_readiness'
  )
}}

-- Training readiness score: composite of HRV, RHR, sleep, and deep sleep
-- Each component scored 0–25 based on percentile rank within the dataset
-- Grain: One row per date with at least one input metric

with daily as (
    select
        date,
        hrv_ms,
        resting_hr_bpm,
        sleep_hours,
        case
            when sleep_hours > 0 then sleep_deep_hours / sleep_hours
            else null
        end as deep_sleep_ratio
    from {{ ref('fct_daily_summary') }}
    where hrv_ms is not null
       or resting_hr_bpm is not null
       or sleep_hours is not null
),

-- Compute rolling 30-day stats for normalization
stats as (
    select
        date,
        hrv_ms,
        resting_hr_bpm,
        sleep_hours,
        deep_sleep_ratio,

        -- HRV: higher is better
        avg(hrv_ms) over (order by date rows between 29 preceding and current row) as hrv_avg_30d,
        stddev(hrv_ms) over (order by date rows between 29 preceding and current row) as hrv_std_30d,

        -- RHR: lower is better
        avg(resting_hr_bpm) over (order by date rows between 29 preceding and current row) as rhr_avg_30d,
        stddev(resting_hr_bpm) over (order by date rows between 29 preceding and current row) as rhr_std_30d,

        -- Sleep: higher is better (capped at goal)
        avg(sleep_hours) over (order by date rows between 29 preceding and current row) as sleep_avg_30d,

        -- Deep sleep ratio: higher is better
        avg(deep_sleep_ratio) over (order by date rows between 29 preceding and current row) as deep_avg_30d

    from daily
),

scored as (
    select
        date,
        hrv_ms,
        resting_hr_bpm,
        sleep_hours,
        deep_sleep_ratio,

        -- HRV score (0-25): z-score clamped to [-2, 2], mapped to [0, 25]
        case
            when hrv_ms is null or hrv_std_30d is null or hrv_std_30d = 0 then null
            else round(least(greatest(
                (hrv_ms - hrv_avg_30d) / hrv_std_30d,
                -2), 2) * 6.25 + 12.5)
        end as hrv_score,

        -- RHR score (0-25): z-score INVERTED (lower RHR = higher score)
        case
            when resting_hr_bpm is null or rhr_std_30d is null or rhr_std_30d = 0 then null
            else round(least(greatest(
                -(resting_hr_bpm - rhr_avg_30d) / rhr_std_30d,
                -2), 2) * 6.25 + 12.5)
        end as rhr_score,

        -- Sleep score (0-25): ratio of sleep to 7h goal, capped at 1.0
        case
            when sleep_hours is null then null
            else round(least(sleep_hours / 7.0, 1.0) * 25)
        end as sleep_score,

        -- Deep sleep score (0-25): ratio vs 30d average, capped
        case
            when deep_sleep_ratio is null or deep_avg_30d is null or deep_avg_30d = 0 then null
            else round(least(deep_sleep_ratio / deep_avg_30d, 1.5) / 1.5 * 25)
        end as deep_score

    from stats
)

select
    date,
    hrv_ms,
    resting_hr_bpm,
    sleep_hours,
    round(deep_sleep_ratio, 3) as deep_sleep_ratio,
    hrv_score,
    rhr_score,
    sleep_score,
    deep_score,
    coalesce(hrv_score, 0) + coalesce(rhr_score, 0) + coalesce(sleep_score, 0) + coalesce(deep_score, 0) as readiness_score
from scored
order by date desc
```

**Step 2: Add schema entry**

Add to `dbt_project/models/marts/schema.yml` after the `fct_weight_rolling_averages` entry:

```yaml
  - name: fct_training_readiness
    description: >
      Composite training readiness score (0-100) based on HRV, RHR, sleep, and deep sleep.
      Each component scores 0-25 using z-score normalization against 30-day rolling baseline.
      Grain: One row per date with at least one cardiovascular/sleep metric.
```

**Step 3: Build and verify**

Run: `set -a && source .env && set +a && cd dbt_project && uv run dbt run --profiles-dir . --select fct_training_readiness`

**Step 4: Commit**

```bash
git add dbt_project/models/marts/fct_training_readiness.sql dbt_project/models/marts/schema.yml
git commit -m "feat: add training readiness score dbt model"
```

---

### Task 2: Add data loader and display on Recovery page

**Files:**
- Modify: `src/dashboard/data.py`
- Modify: `src/dashboard/pages/1_Recovery.py`

**Step 1: Add data loader**

Add to `src/dashboard/data.py` after `load_daily_workouts()`:

```python
@st.cache_data(ttl=timedelta(hours=1), show_spinner="Loading readiness data...")
def load_training_readiness() -> pl.DataFrame:
    """Load training readiness scores."""
    return load_parquet("fct_training_readiness")
```

**Step 2: Add readiness display to Recovery page**

Import `load_training_readiness` in the imports and add a "Training Readiness" section at the top of the page, before the Daily Breakdown table. This should be the very first thing on the page — a single prominent card showing today's score with a small sparkline-style trend.

```python
# At the very top after data loading (after line 31)
from dashboard.data import load_daily_summary, load_daily_workouts, load_training_readiness

# Before the Daily Breakdown header
df_readiness = load_training_readiness()
if df_readiness.height > 0:
    recent_readiness = df_readiness.filter(
        (pl.col("date") >= pl.lit(start_date)) & (pl.col("date") <= pl.lit(end_date))
    )
    if recent_readiness.height > 0:
        st.header("Training Readiness")
        latest = recent_readiness.sort("date", descending=True).head(1)
        score = latest["readiness_score"].item()
        if score is not None:
            score = float(score)
            if score >= 75:
                color, label = "#00CC96", "Ready"
            elif score >= 50:
                color, label = "#FFA500", "Moderate"
            else:
                color, label = "#EF553B", "Fatigued"

            r1, r2, r3, r4, r5 = st.columns(5)
            with r1:
                st.markdown(
                    f'<p style="font-size:3rem;font-weight:700;color:{color};margin:0;">'
                    f'{score:.0f}</p>'
                    f'<p style="font-size:1rem;color:{color};margin:0;">{label}</p>',
                    unsafe_allow_html=True,
                )
            with r2:
                hrv_s = latest["hrv_score"].item()
                st.metric("HRV", f"{hrv_s:.0f}/25" if hrv_s else "—")
            with r3:
                rhr_s = latest["rhr_score"].item()
                st.metric("RHR", f"{rhr_s:.0f}/25" if rhr_s else "—")
            with r4:
                sleep_s = latest["sleep_score"].item()
                st.metric("Sleep", f"{sleep_s:.0f}/25" if sleep_s else "—")
            with r5:
                deep_s = latest["deep_score"].item()
                st.metric("Deep", f"{deep_s:.0f}/25" if deep_s else "—")

            # Trend chart
            if recent_readiness.height > 1:
                trend_data = (
                    recent_readiness.filter(pl.col("readiness_score").is_not_null())
                    .with_columns(
                        pl.col("date").cast(pl.Date).dt.strftime("%Y-%m-%d").alias("Date")
                    )
                    .select(["Date", "readiness_score"])
                    .sort("Date")
                    .to_pandas()
                )
                line = (
                    alt.Chart(trend_data)
                    .mark_area(
                        line=True,
                        opacity=0.3,
                        color="#636EFA",
                    )
                    .encode(
                        x=alt.X("Date:N", sort=None, title="Date"),
                        y=alt.Y("readiness_score:Q", title="Score", scale=alt.Scale(domain=[0, 100])),
                    )
                )
                text = (
                    alt.Chart(trend_data)
                    .mark_text(dy=-10, fontSize=11, color="white")
                    .encode(
                        x=alt.X("Date:N", sort=None),
                        y=alt.Y("readiness_score:Q"),
                        text=alt.Text("readiness_score:Q", format=".0f"),
                    )
                )
                zones = alt.Chart(trend_data).mark_rect(opacity=0.05).encode(
                    y=alt.datum(75), y2=alt.datum(100), color=alt.value("#00CC96")
                ) + alt.Chart(trend_data).mark_rect(opacity=0.05).encode(
                    y=alt.datum(50), y2=alt.datum(75), color=alt.value("#FFA500")
                ) + alt.Chart(trend_data).mark_rect(opacity=0.05).encode(
                    y=alt.datum(0), y2=alt.datum(50), color=alt.value("#EF553B")
                )
                st.altair_chart(zones + line + text, width="stretch")

        st.caption("*Score: 75–100 Ready, 50–75 Moderate, <50 Fatigued. Based on HRV, RHR, sleep, and deep sleep ratio vs 30-day baseline.*")
        st.divider()
```

**Step 3: Run lint**

Run: `uv run ruff check --fix src/dashboard/pages/1_Recovery.py src/dashboard/data.py && uv run ruff format src/dashboard/pages/1_Recovery.py src/dashboard/data.py`

**Step 4: Commit**

```bash
git add src/dashboard/data.py src/dashboard/pages/1_Recovery.py
git commit -m "feat: add training readiness score to Recovery page"
```
