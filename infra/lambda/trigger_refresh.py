"""Trigger the refresh-data GitHub Actions workflow from an S3 event.

Invoked by S3 ObjectCreated notifications on landing/health/*.json. Fetches
a GitHub PAT from SSM Parameter Store (cached across warm invocations) and
dispatches the refresh-data.yml workflow on main. Any SSM or GitHub API
failure raises so it surfaces in CloudWatch logs and metrics.

The ingest pipeline itself writes a Delta table under
landing/health/health_metrics/, and every Delta commit creates
_delta_log/<version>.json objects that match the notification filter
(prefix landing/health/, suffix .json). Those keys are skipped here so a
workflow run's own writes never dispatch the next run (infinite loop).

Runtime: python3.12. Dependencies: stdlib + boto3 (bundled in the Lambda
runtime), so the function deploys as a single-file zip.
"""

from __future__ import annotations

import json
import os
import urllib.request

_ssm_client = None
_cached_token = None

# Prefix the ingest pipeline writes its Delta table to. Objects here (including
# _delta_log/*.json commit files) are pipeline output, not phone uploads.
_PIPELINE_OUTPUT_PREFIX = "landing/health/health_metrics/"


def _is_pipeline_write(key: str) -> bool:
    """True for keys written by the pipeline itself (must not retrigger it)."""
    return key.startswith(_PIPELINE_OUTPUT_PREFIX) or "_delta_log/" in key


def _get_ssm_client():
    """Create the SSM client lazily so tests can patch it in.

    boto3 is imported here (not at module level) because it is bundled in
    the Lambda runtime but not installed in the local dev environment.
    """
    global _ssm_client
    if _ssm_client is None:
        import boto3

        _ssm_client = boto3.client("ssm")
    return _ssm_client


def _get_github_token() -> str:
    """Fetch the GitHub PAT from SSM, caching it across warm invocations."""
    global _cached_token
    if _cached_token is None:
        param_name = os.environ["SSM_PARAM_NAME"]
        response = _get_ssm_client().get_parameter(Name=param_name, WithDecryption=True)
        _cached_token = response["Parameter"]["Value"]
    return _cached_token


def lambda_handler(event, context):
    keys = [record["s3"]["object"]["key"] for record in event.get("Records", []) if "s3" in record]
    print(f"Triggered by S3 object(s): {keys}")

    upload_keys = [key for key in keys if not _is_pipeline_write(key)]
    skipped_keys = [key for key in keys if _is_pipeline_write(key)]
    if skipped_keys:
        print(f"Skipping pipeline-written object(s): {skipped_keys}")
    if not upload_keys:
        print("No new export uploads in event; not dispatching.")
        return {"dispatched": False, "keys": keys}

    owner = os.environ["GITHUB_OWNER"]
    repo = os.environ["GITHUB_REPO"]
    token = _get_github_token()

    url = (
        f"https://api.github.com/repos/{owner}/{repo}/actions/workflows/refresh-data.yml/dispatches"
    )
    request = urllib.request.Request(
        url,
        data=json.dumps({"ref": "main"}).encode("utf-8"),
        method="POST",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "apple-health-refresh-trigger",
            "Content-Type": "application/json",
        },
    )
    # urlopen raises HTTPError for most non-2xx codes; the explicit status
    # check below covers any that slip through.
    with urllib.request.urlopen(request) as response:
        status = response.status
    if not 200 <= status < 300:
        raise RuntimeError(f"GitHub workflow dispatch failed: HTTP {status}")

    print(f"Dispatched refresh-data.yml on {owner}/{repo} (HTTP {status})")
    return {"dispatched": True, "keys": keys}
