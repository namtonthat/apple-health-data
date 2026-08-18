"""Tests for shared pipeline config: run_s3_pipeline and get_duckdb_connection."""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from pipelines import config


class _FakeLoadInfo:
    load_packages: list = []


class _FakePipeline:
    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.run_calls: list = []

    def run(self, source, **kwargs):
        self.run_calls.append((source, kwargs))
        return _FakeLoadInfo()


def _patch_pipeline_and_destination(monkeypatch):
    """Replace dlt.pipeline and the filesystem destination factory with fakes,
    returning the dicts of kwargs each was called with."""
    pipeline_calls: dict = {}
    destination_calls: dict = {}

    def fake_pipeline(**kwargs):
        pipeline_calls.update(kwargs)
        return _FakePipeline(**kwargs)

    def fake_filesystem(**kwargs):
        destination_calls.update(kwargs)
        return "FAKE_DESTINATION"

    monkeypatch.setattr(config.dlt, "pipeline", fake_pipeline)
    monkeypatch.setattr(config, "filesystem", fake_filesystem)
    return pipeline_calls, destination_calls


def _set_aws_env(monkeypatch):
    monkeypatch.setenv("S3_BUCKET_NAME", "test-bucket")
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "test-key")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "test-secret")


def test_run_s3_pipeline_builds_expected_destination_and_dataset(monkeypatch, capsys):
    _set_aws_env(monkeypatch)
    pipeline_calls, destination_calls = _patch_pipeline_and_destination(monkeypatch)

    config.run_s3_pipeline("hevy_to_landing", "hevy", source=object())

    assert pipeline_calls["pipeline_name"] == "hevy_to_landing"
    assert pipeline_calls["dataset_name"] == "hevy"
    assert pipeline_calls["destination"] == "FAKE_DESTINATION"
    assert destination_calls["bucket_url"] == "s3://test-bucket/landing"

    out = capsys.readouterr().out
    assert "Destination: s3://test-bucket/landing/hevy/" in out


def test_run_s3_pipeline_defaults_extraction_date_to_today(monkeypatch, capsys):
    _set_aws_env(monkeypatch)
    _patch_pipeline_and_destination(monkeypatch)

    config.run_s3_pipeline("hevy_to_landing", "hevy", source=object(), extraction_date=None)

    expected_date = datetime.now(ZoneInfo("Australia/Melbourne")).date().isoformat()
    out = capsys.readouterr().out
    assert f"Extraction date: {expected_date}" in out


def test_run_s3_pipeline_honours_explicit_extraction_date(monkeypatch, capsys):
    _set_aws_env(monkeypatch)
    _patch_pipeline_and_destination(monkeypatch)

    config.run_s3_pipeline("hevy_to_landing", "hevy", source=object(), extraction_date="2026-01-15")

    out = capsys.readouterr().out
    assert "Extraction date: 2026-01-15" in out


def test_get_duckdb_connection_is_idempotent(monkeypatch):
    """Repeated calls must return the same connection and only open/configure it once."""
    _set_aws_env(monkeypatch)

    class FakeConn:
        def __init__(self):
            self.executed: list[str] = []

        def execute(self, sql):
            self.executed.append(sql)
            return self

    created: list[FakeConn] = []

    def fake_connect(*_args, **_kwargs):
        conn = FakeConn()
        created.append(conn)
        return conn

    monkeypatch.setattr(config.duckdb, "connect", fake_connect)
    config.get_duckdb_connection.cache_clear()

    conn1 = config.get_duckdb_connection()
    conn2 = config.get_duckdb_connection()

    assert conn1 is conn2
    assert len(created) == 1
    assert any("CREATE OR REPLACE SECRET" in sql for sql in conn1.executed)

    config.get_duckdb_connection.cache_clear()
