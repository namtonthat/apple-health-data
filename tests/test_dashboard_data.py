from __future__ import annotations

import duckdb
import polars as pl
import pytest

from dashboard import data


class _FakeArrowResult:
    def __init__(self, table):
        self._table = table

    def fetch_arrow_table(self):
        return self._table


class _FakeCursor:
    """Stand-in for ``conn.cursor()`` -- shares the parent connection's canned
    result/error but tracks its own close() independently of the connection."""

    def __init__(self, conn: "_FakeConnection"):
        self._conn = conn
        self.closed = False

    def execute(self, query, params=None):
        self._conn.executed.append((query, params))
        if self._conn.error is not None:
            raise self._conn.error
        return _FakeArrowResult(self._conn.result)

    def close(self):
        self.closed = True


class _FakeConnection:
    """Stand-in for the shared, cached DuckDB connection (see ``data.get_connection``)."""

    def __init__(self, *, result=None, error: Exception | None = None):
        self.result = result
        self.error = error
        self.closed = False
        self.executed: list[tuple[str, list | None]] = []
        self.cursors: list[_FakeCursor] = []

    def cursor(self) -> _FakeCursor:
        cursor = _FakeCursor(self)
        self.cursors.append(cursor)
        return cursor

    def close(self):
        self.closed = True


def test_load_parquet_executes_query_via_cursor(monkeypatch):
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


def test_load_parquet_closes_its_cursor_but_leaves_shared_connection_open(monkeypatch):
    conn = _FakeConnection(result=pl.DataFrame({"value": [1]}).to_arrow())

    monkeypatch.setattr(data, "get_connection", lambda: conn)
    monkeypatch.setattr(data, "get_s3_path", lambda table_name: f"s3://bucket/{table_name}")

    data.load_parquet("recent/fct_daily_summary")

    # The connection is shared across loaders/calls (st.cache_resource) and must
    # not be closed per call; only the per-call cursor closes.
    assert conn.closed is False
    assert len(conn.cursors) == 1
    assert conn.cursors[0].closed is True


def test_load_parquet_returns_empty_dataframe_on_missing_files(monkeypatch):
    conn = _FakeConnection(error=duckdb.IOException("No files found matching path"))

    monkeypatch.setattr(data, "get_connection", lambda: conn)
    monkeypatch.setattr(data, "get_s3_path", lambda table_name: f"s3://bucket/{table_name}")

    result = data.load_parquet("recent/fct_daily_summary")

    assert result.is_empty()
    assert conn.closed is False
    assert conn.cursors[0].closed is True


def test_load_parquet_reraises_other_duckdb_errors(monkeypatch):
    conn = _FakeConnection(error=duckdb.CatalogException("Table not found"))

    monkeypatch.setattr(data, "get_connection", lambda: conn)
    monkeypatch.setattr(data, "get_s3_path", lambda table_name: f"s3://bucket/{table_name}")

    with pytest.raises(duckdb.CatalogException):
        data.load_parquet("recent/fct_daily_summary")

    assert conn.cursors[0].closed is True
