"""Tests for the OpenPowerlifting profile page parser and run_pipeline."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

from pipelines import openpowerlifting as op

FIXTURES = Path(__file__).parent / "fixtures"


def _fake_response(html: str) -> MagicMock:
    response = MagicMock()
    response.text = html
    response.raise_for_status.return_value = None
    return response


def test_parses_competitions_and_personal_bests(monkeypatch):
    html = (FIXTURES / "openpowerlifting_profile.html").read_text()
    monkeypatch.setattr(op.requests, "get", lambda *a, **k: _fake_response(html))

    data = op.parse_openpowerlifting_page("https://openpowerlifting.org/u/janelifter")

    assert data["athlete_name"] == "Jane Lifter"
    assert len(data["competitions"]) == 2
    assert data["competitions"][0]["squat"] == "150.5kg"

    # Personal bests take the max across all competitions.
    assert data["personal_bests"] == {
        "squat_kg": 160.0,
        "bench_kg": 95.0,
        "deadlift_kg": 190.0,
        "total_kg": 445.0,
    }


def test_missing_lift_columns_degrade_personal_bests_to_zero(monkeypatch):
    """Documents the current fallback behavior: if the table has no squat/bench/
    deadlift column under any of the recognized names, those personal bests
    silently degrade to 0 instead of raising — so markup drift on the
    OpenPowerlifting site fails quietly. Total still parses since its column
    is present. This test exists to catch that drift (a future fix might
    surface a warning instead of silently zeroing).
    """
    html = (FIXTURES / "openpowerlifting_profile_missing_lifts.html").read_text()
    monkeypatch.setattr(op.requests, "get", lambda *a, **k: _fake_response(html))

    data = op.parse_openpowerlifting_page("https://openpowerlifting.org/u/janelifter")

    assert data["personal_bests"]["squat_kg"] == 0
    assert data["personal_bests"]["bench_kg"] == 0
    assert data["personal_bests"]["deadlift_kg"] == 0
    assert data["personal_bests"]["total_kg"] == 420.5


def test_no_table_returns_empty_result(monkeypatch):
    monkeypatch.setattr(
        op.requests, "get", lambda *a, **k: _fake_response("<title>Jane | OpenPowerlifting</title>")
    )

    data = op.parse_openpowerlifting_page("https://openpowerlifting.org/u/janelifter")

    assert data == {"athlete_name": "Jane", "competitions": [], "personal_bests": {}}


def test_run_pipeline_fetches_and_parses_page_only_once(monkeypatch):
    """Both resources must share a single fetch+parse of the profile page."""
    html = (FIXTURES / "openpowerlifting_profile.html").read_text()
    call_count = {"n": 0}

    def fake_get(*_a, **_k):
        call_count["n"] += 1
        return _fake_response(html)

    monkeypatch.setattr(op.requests, "get", fake_get)
    monkeypatch.setenv("OPENPOWERLIFTING_URL", "https://openpowerlifting.org/u/janelifter")
    monkeypatch.setattr(op, "OPENPOWERLIFTING_URL", "https://openpowerlifting.org/u/janelifter")
    monkeypatch.setenv("S3_BUCKET_NAME", "test-bucket")

    captured_resources = {}

    class FakePipeline:
        def run(self, resources, **kwargs):
            captured_resources["resources"] = resources
            return "FAKE_LOAD_INFO"

    monkeypatch.setattr(op.dlt, "pipeline", lambda **kwargs: FakePipeline())

    load_info = op.run_pipeline()

    assert call_count["n"] == 1
    assert load_info == "FAKE_LOAD_INFO"
    # Both dlt resources were built (personal_bests, competitions) off the one fetch.
    assert len(captured_resources["resources"]) == 2


def test_run_pipeline_skips_when_url_not_configured(monkeypatch):
    monkeypatch.setattr(op, "OPENPOWERLIFTING_URL", "")

    def fail_get(*_a, **_k):
        raise AssertionError("should not fetch when URL is not configured")

    monkeypatch.setattr(op.requests, "get", fail_get)

    assert op.run_pipeline() is None
