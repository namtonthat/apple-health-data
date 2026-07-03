"""Tests for the Apple Health dlt source's S3 file selection."""

from __future__ import annotations

from unittest.mock import MagicMock

from pipelines.sources.apple_health import _list_health_files


def _s3_with(files: list[str]) -> MagicMock:
    s3 = MagicMock()
    s3.glob.return_value = files
    return s3


def test_lists_export_files_sorted():
    s3 = _s3_with(
        [
            "bucket/landing/health/2026-07-02T22:00:16.342882+00:00.json",
            "bucket/landing/health/2026-07-01T21:44:35.356884+00:00.json",
        ]
    )
    files = _list_health_files(s3, "bucket")
    assert files == [
        "bucket/landing/health/2026-07-01T21:44:35.356884+00:00.json",
        "bucket/landing/health/2026-07-02T22:00:16.342882+00:00.json",
    ]


def test_ignores_non_export_files():
    """Stray JSON (e.g. smoke-test uploads) must never shadow the latest export.

    latest_only ingestion takes files[-1]; names like 'trigger-test.json' sort
    after timestamp names lexicographically, so without filtering they would be
    selected as the 'latest export' and the run would ingest nothing.
    """
    s3 = _s3_with(
        [
            "bucket/landing/health/2026-07-01T21:44:35.356884+00:00.json",
            "bucket/landing/health/2026-07-02T22:00:16.342882+00:00.json",
            "bucket/landing/health/trigger-smoke-test.json",
            "bucket/landing/health/notes.json",
        ]
    )
    files = _list_health_files(s3, "bucket")
    assert files[-1] == "bucket/landing/health/2026-07-02T22:00:16.342882+00:00.json"
    assert len(files) == 2
