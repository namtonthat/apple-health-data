"""Receive Apple Health exports over HTTPS and land them in S3.

Target of a Lambda Function URL that Health Auto Export POSTs the export JSON
to. Writes the payload verbatim to s3://{S3_BUCKET}/landing/health/ named with
the UTC receive time (e.g. 2026-07-03T08:00:16.342882+00:00.json) — the same
scheme the ingest pipeline's latest-export selection expects. The resulting
S3 object then fires the apple-health-refresh-trigger Lambda, so an upload
kicks off the whole refresh.

Auth: Function URLs are public (AuthType NONE); require a shared token so the
unguessable URL isn't the only barrier. The token may arrive as ?token=... or
an x-api-key header. INGEST_TOKEN must be set — there is no unauthenticated mode.

Runtime: python3.12, stdlib + runtime-bundled boto3, single-file zip.
"""

from __future__ import annotations

import base64
import hmac
import json
import os
from datetime import datetime, timezone

_s3_client = None


def _get_s3_client():
    global _s3_client
    if _s3_client is None:
        import boto3

        _s3_client = boto3.client("s3")
    return _s3_client


def _response(status: int, body: dict) -> dict:
    return {
        "statusCode": status,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body),
    }


def _extract_token(event: dict) -> str:
    query = event.get("queryStringParameters") or {}
    headers = event.get("headers") or {}
    headers = {k.lower(): v for k, v in headers.items()}
    return query.get("token") or headers.get("x-api-key") or ""


def lambda_handler(event, context):
    expected = os.environ["INGEST_TOKEN"]
    if not hmac.compare_digest(_extract_token(event), expected):
        return _response(403, {"error": "forbidden"})

    body = event.get("body") or ""
    if event.get("isBase64Encoded"):
        body = base64.b64decode(body).decode("utf-8")

    # Reject non-JSON early so a misconfigured client gets a clear error
    # instead of landing junk that the pipeline then has to skip.
    try:
        json.loads(body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return _response(400, {"error": "body is not valid JSON"})

    bucket = os.environ["S3_BUCKET"]
    key = f"landing/health/{datetime.now(timezone.utc).isoformat()}.json"
    _get_s3_client().put_object(
        Bucket=bucket, Key=key, Body=body.encode("utf-8"), ContentType="application/json"
    )

    print(f"Stored export at s3://{bucket}/{key} ({len(body)} bytes)")
    return _response(200, {"message": "stored", "key": key})
