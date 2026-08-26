"""Tests for the OpenPowerlifting lifter CSV pipeline."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

from pipelines import openpowerlifting as op

FIXTURES = Path(__file__).parent / "fixtures"


def _fake_response(text: str) -> MagicMock:
    response = MagicMock()
    response.text = text
    response.raise_for_status.return_value = None
    return response


def test_csv_url_from_profile_url():
    assert (
        op.csv_url_from_profile("https://www.openpowerlifting.org/u/janelifter")
        == "https://www.openpowerlifting.org/api/liftercsv/janelifter"
    )
    # Trailing slash must not produce an empty username.
    assert (
        op.csv_url_from_profile("https://www.openpowerlifting.org/u/janelifter/")
        == "https://www.openpowerlifting.org/api/liftercsv/janelifter"
    )


def test_fetch_lifter_rows_parses_csv_and_nulls_empty_fields(monkeypatch):
    csv_text = (FIXTURES / "openpowerlifting_lifter.csv").read_text()
    monkeypatch.setattr(op.requests, "get", lambda *a, **k: _fake_response(csv_text))

    rows = op.fetch_lifter_rows("https://www.openpowerlifting.org/api/liftercsv/janelifter")

    assert len(rows) == 2
    assert rows[0]["Name"] == "Jane Lifter"
    assert rows[0]["MeetName"] == "Elemental Ice Challenge"
    assert rows[0]["Date"] == "2026-07-18"
    assert rows[0]["Best3DeadliftKg"] == "225"
    # Empty CSV fields land as NULL, not empty string.
    assert rows[0]["Squat4Kg"] is None
    assert rows[1]["ParentFederation"] is None


def test_run_pipeline_loads_competitions_from_csv(monkeypatch):
    csv_text = (FIXTURES / "openpowerlifting_lifter.csv").read_text()
    requested_urls = []

    def fake_get(url, *a, **k):
        requested_urls.append(url)
        return _fake_response(csv_text)

    monkeypatch.setattr(op.requests, "get", fake_get)
    monkeypatch.setattr(op, "OPENPOWERLIFTING_URL", "https://www.openpowerlifting.org/u/janelifter")
    monkeypatch.setenv("S3_BUCKET_NAME", "test-bucket")

    captured = {}

    class FakePipeline:
        def run(self, resources, **kwargs):
            captured["resources"] = resources
            captured["run_kwargs"] = kwargs
            return "FAKE_LOAD_INFO"

    monkeypatch.setattr(op.dlt, "pipeline", lambda **kwargs: FakePipeline())

    load_info = op.run_pipeline()

    assert load_info == "FAKE_LOAD_INFO"
    assert requested_urls == ["https://www.openpowerlifting.org/api/liftercsv/janelifter"]
    rows = list(captured["resources"])
    assert len(rows) == 2
    assert rows[0]["MeetName"] == "Elemental Ice Challenge"
    assert captured["run_kwargs"]["loader_file_format"] == "parquet"


def test_run_pipeline_skips_when_url_not_configured(monkeypatch):
    monkeypatch.setattr(op, "OPENPOWERLIFTING_URL", "")

    def fail_get(*_a, **_k):
        raise AssertionError("should not fetch when URL is not configured")

    monkeypatch.setattr(op.requests, "get", fail_get)

    assert op.run_pipeline() is None
