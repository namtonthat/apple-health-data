from datetime import datetime

import polars as pl

from dashboard.helpers import compute_avg_sleep_time


def test_compute_avg_sleep_time_midnight():
    df = pl.DataFrame(
        {
            "sleep_times": [
                datetime(2023, 1, 1, 23, 30),
                datetime(2023, 1, 2, 0, 30),
            ]
        }
    )

    result = compute_avg_sleep_time(df)

    expected = datetime.today().replace(hour=0, minute=0, second=0, microsecond=0)
    assert result == expected
