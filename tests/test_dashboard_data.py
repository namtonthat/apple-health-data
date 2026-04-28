from __future__ import annotations

import polars as pl

from dashboard import data


class _FakeArrowResult:
    def __init__(self, table):
        self._table = table

    def fetch_arrow_table(self):
        return self._table


class _FakeConnection:
    def __init__(self, *, result=None, error: Exception | None = None):
        self.result = result
        self.error = error
        self.closed = False
        self.executed: list[tuple[str, list | None]] = []

    def execute(self, query, params=None):
        self.executed.append((query, params))
        if self.error is not None:
            raise self.error
        return _FakeArrowResult(self.result)

    def close(self):
        self.closed = True


def test_load_parquet_executes_query_and_closes_connection(monkeypatch):
    expected = pl.DataFrame({"value": [1, 2]})
    conn = _FakeConnection(result=expected.to_arrow())

    monkeypatch.setattr(data, "get_connection", lambda: conn)
    monkeypatch.setattr(data, "get_s3_path", lambda table_name: f"s3://bucket/{table_name}")

    result = data.load_parquet(
        "recent/fct_daily_summary",
        "SELECT * FROM read_parquet('{path}') WHERE metric_date BETWEEN ? AND ?",
        ["2026-01-01", "2026-01-14"],
    )

    assert result.to_dict(as_series=False) == expected.to_dict(as_series=False)
    assert conn.executed == [
        (
            "SELECT * FROM read_parquet('s3://bucket/recent/fct_daily_summary') "
            "WHERE metric_date BETWEEN ? AND ?",
            ["2026-01-01", "2026-01-14"],
        )
    ]
    assert conn.closed is True


def test_load_parquet_returns_empty_dataframe_and_closes_on_missing_files(monkeypatch):
    conn = _FakeConnection(error=Exception("No files found matching path"))

    monkeypatch.setattr(data, "get_connection", lambda: conn)
    monkeypatch.setattr(data, "get_s3_path", lambda table_name: f"s3://bucket/{table_name}")

    result = data.load_parquet("recent/fct_daily_summary")

    assert result.is_empty()
    assert conn.closed is True
