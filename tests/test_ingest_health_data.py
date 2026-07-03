"""Tests for the ingest_health_data Function URL Lambda handler."""

from __future__ import annotations

import base64
import json
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

LAMBDA_DIR = Path(__file__).resolve().parents[1] / "infra" / "lambda"
if str(LAMBDA_DIR) not in sys.path:
    sys.path.insert(0, str(LAMBDA_DIR))

import ingest_health_data  # noqa: E402


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    monkeypatch.setenv("S3_BUCKET", "test-bucket")
    monkeypatch.setenv("INGEST_TOKEN", "sekrit")
    ingest_health_data._s3_client = MagicMock()
    yield
    ingest_health_data._s3_client = None


def _event(body: str, token: str = "sekrit", b64: bool = False, header: bool = False) -> dict:
    event: dict = {"body": body, "isBase64Encoded": b64}
    if header:
        event["headers"] = {"X-Api-Key": token}
    else:
        event["queryStringParameters"] = {"token": token}
    return event


def test_stores_export_under_landing_health_with_utc_timestamp_name():
    payload = json.dumps({"data": {"metrics": []}})
    result = ingest_health_data.lambda_handler(_event(payload), None)

    assert result["statusCode"] == 200
    call = ingest_health_data._s3_client.put_object.call_args.kwargs
    assert call["Bucket"] == "test-bucket"
    assert call["Key"].startswith("landing/health/")
    assert call["Key"].endswith("+00:00.json")
    assert call["Body"] == payload.encode("utf-8")
    # The ingest pipeline only lists timestamp-named files; the key must match.
    from pipelines.sources.apple_health import _EXPORT_FILENAME_RE

    assert _EXPORT_FILENAME_RE.match(call["Key"].rsplit("/", 1)[-1])


def test_accepts_base64_encoded_body():
    payload = json.dumps({"data": {}})
    encoded = base64.b64encode(payload.encode()).decode()
    result = ingest_health_data.lambda_handler(_event(encoded, b64=True), None)

    assert result["statusCode"] == 200
    assert ingest_health_data._s3_client.put_object.call_args.kwargs["Body"] == payload.encode()


def test_accepts_token_via_header():
    result = ingest_health_data.lambda_handler(_event("{}", header=True), None)
    assert result["statusCode"] == 200


def test_rejects_bad_token_without_writing():
    result = ingest_health_data.lambda_handler(_event("{}", token="wrong"), None)
    assert result["statusCode"] == 403
    ingest_health_data._s3_client.put_object.assert_not_called()


def test_rejects_invalid_json_without_writing():
    result = ingest_health_data.lambda_handler(_event("not json"), None)
    assert result["statusCode"] == 400
    ingest_health_data._s3_client.put_object.assert_not_called()
