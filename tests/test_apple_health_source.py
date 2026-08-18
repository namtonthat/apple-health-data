"""Tests for the Apple Health dlt source's S3 file selection and parsing."""

from __future__ import annotations

import io
import json
from unittest.mock import MagicMock

from pipelines.sources import apple_health as ah
from pipelines.sources.apple_health import _list_health_files


def _s3_with(files: list[str]) -> MagicMock:
    s3 = MagicMock()
    s3.glob.return_value = files
    return s3


class _FakeS3File:
    """Minimal context-manager stand-in for s3fs.S3FileSystem.open()."""

    def __init__(self, content: str):
        self._content = content

    def __enter__(self):
        return io.StringIO(self._content)

    def __exit__(self, *_exc):
        return False


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


def test_malformed_datapoint_is_skipped_rest_of_file_still_parses(monkeypatch):
    """A single non-numeric `qty` must not abort the whole file's metrics.

    Previously `float(raw_value)` was unguarded, so one bad point raised and
    aborted the entire resource for the day.
    """
    s3 = _s3_with(["bucket/landing/health/2026-07-01T00:00:00+00:00.json"])
    payload = {
        "data": {
            "metrics": [
                {
                    "name": "step_count",  # allowlisted metric
                    "units": "count",
                    "data": [
                        {
                            "date": "2026-07-01 00:00:00 +0000",
                            "qty": "not-a-number",
                            "source": "iPhone",
                        },
                        {
                            "date": "2026-07-02 00:00:00 +0000",
                            "qty": 100,
                            "source": "iPhone",
                        },
                    ],
                }
            ]
        }
    }
    s3.open.return_value = _FakeS3File(json.dumps(payload))
    monkeypatch.setattr(ah, "get_s3_client", lambda *a, **k: s3)

    rows = list(ah.health_metrics_resource("bucket"))

    assert len(rows) == 1
    assert rows[0]["metric_date"] == "2026-07-02"
    assert rows[0]["value"] == 100.0


def test_non_allowlisted_metric_is_skipped():
    """Metrics not consumed by any int_health__ model must not be ingested."""
    assert "not_a_real_metric" not in ah.ALLOWED_METRIC_NAMES
    assert "step_count" in ah.ALLOWED_METRIC_NAMES
