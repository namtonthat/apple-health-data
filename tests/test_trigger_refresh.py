"""Unit tests for the S3-triggered refresh Lambda handler.

No network and no real AWS: the SSM client and urllib.request.urlopen are
mocked. The handler lives in infra/lambda/ (not on the default test path),
so this module adds that directory to sys.path before importing it.
"""

from __future__ import annotations

import json
import sys
import urllib.error
from pathlib import Path
from unittest.mock import MagicMock

import pytest

LAMBDA_DIR = Path(__file__).resolve().parents[1] / "infra" / "lambda"
if str(LAMBDA_DIR) not in sys.path:
    sys.path.insert(0, str(LAMBDA_DIR))

import trigger_refresh  # noqa: E402

S3_EVENT = {
    "Records": [
        {
            "s3": {
                "bucket": {"name": "api-health-data-ntonthat"},
                "object": {"key": "landing/health/HealthAutoExport-2026-07-03.json"},
            }
        }
    ]
}


@pytest.fixture(autouse=True)
def _clean_state(monkeypatch):
    """Reset module-level caches and provide the required env vars."""
    monkeypatch.setattr(trigger_refresh, "_ssm_client", None)
    monkeypatch.setattr(trigger_refresh, "_cached_token", None)
    monkeypatch.setenv("GITHUB_OWNER", "namtonthat")
    monkeypatch.setenv("GITHUB_REPO", "apple-health-data")
    monkeypatch.setenv("SSM_PARAM_NAME", "/apple-health-data/github-pat")


def _mock_ssm(token: str = "test-pat") -> MagicMock:
    ssm = MagicMock()
    ssm.get_parameter.return_value = {"Parameter": {"Value": token}}
    return ssm


class _FakeResponse:
    def __init__(self, status: int):
        self.status = status

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def _patch_urlopen(monkeypatch, status: int = 204) -> list:
    """Replace urllib.request.urlopen; return the list of captured requests."""
    requests = []

    def fake_urlopen(request):
        requests.append(request)
        return _FakeResponse(status)

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    return requests


def test_dispatch_request_url_method_headers_body(monkeypatch):
    monkeypatch.setattr(trigger_refresh, "_ssm_client", _mock_ssm())
    requests = _patch_urlopen(monkeypatch, status=204)

    trigger_refresh.lambda_handler(S3_EVENT, None)

    assert len(requests) == 1
    request = requests[0]
    assert request.full_url == (
        "https://api.github.com/repos/namtonthat/apple-health-data"
        "/actions/workflows/refresh-data.yml/dispatches"
    )
    assert request.get_method() == "POST"
    assert request.get_header("Authorization") == "Bearer test-pat"
    assert request.get_header("Accept") == "application/vnd.github+json"
    assert request.get_header("X-github-api-version") == "2022-11-28"
    assert request.get_header("User-agent")  # GitHub requires a User-Agent
    assert json.loads(request.data) == {"ref": "main"}


def test_non_2xx_github_response_raises(monkeypatch):
    """Defensive backstop: a returned (not raised) non-2xx status still raises."""
    monkeypatch.setattr(trigger_refresh, "_ssm_client", _mock_ssm())
    _patch_urlopen(monkeypatch, status=500)

    with pytest.raises(RuntimeError, match="500"):
        trigger_refresh.lambda_handler(S3_EVENT, None)


def test_github_http_error_propagates(monkeypatch):
    """Real failure path: urlopen raises HTTPError for 4xx/5xx (bad PAT, wrong repo).

    The default urllib opener never returns a non-2xx response object — it
    raises HTTPError — so this, not the status backstop, is the production
    failure mode. The handler must let it propagate (no swallow) so the Lambda
    invocation fails and lands in CloudWatch.
    """
    monkeypatch.setattr(trigger_refresh, "_ssm_client", _mock_ssm())

    def raising_urlopen(request):
        raise urllib.error.HTTPError(request.full_url, 404, "Not Found", hdrs=None, fp=None)

    monkeypatch.setattr("urllib.request.urlopen", raising_urlopen)

    with pytest.raises(urllib.error.HTTPError):
        trigger_refresh.lambda_handler(S3_EVENT, None)


@pytest.mark.parametrize(
    "key",
    [
        # Delta commit written by the pipeline's own ingest step.
        "landing/health/health_metrics/_delta_log/00000000000000000042.json",
        # Anything else under the pipeline's Delta table prefix.
        "landing/health/health_metrics/part-00000.json",
    ],
)
def test_pipeline_written_objects_do_not_dispatch(monkeypatch, key):
    """The pipeline's own writes match the S3 filter; they must not retrigger it."""
    monkeypatch.setattr(trigger_refresh, "_ssm_client", _mock_ssm())
    requests = _patch_urlopen(monkeypatch, status=204)
    event = {"Records": [{"s3": {"object": {"key": key}}}]}

    result = trigger_refresh.lambda_handler(event, None)

    assert requests == []  # dispatch never attempted
    assert result["dispatched"] is False


def test_mixed_event_with_real_upload_still_dispatches(monkeypatch):
    monkeypatch.setattr(trigger_refresh, "_ssm_client", _mock_ssm())
    requests = _patch_urlopen(monkeypatch, status=204)
    event = {
        "Records": [
            {"s3": {"object": {"key": "landing/health/health_metrics/_delta_log/1.json"}}},
            {"s3": {"object": {"key": "landing/health/HealthAutoExport-2026-07-03.json"}}},
        ]
    }

    result = trigger_refresh.lambda_handler(event, None)

    assert len(requests) == 1
    assert result["dispatched"] is True


def test_ssm_token_cached_across_invocations(monkeypatch):
    ssm = _mock_ssm()
    monkeypatch.setattr(trigger_refresh, "_ssm_client", ssm)
    _patch_urlopen(monkeypatch, status=204)

    trigger_refresh.lambda_handler(S3_EVENT, None)
    trigger_refresh.lambda_handler(S3_EVENT, None)

    assert ssm.get_parameter.call_count == 1
    ssm.get_parameter.assert_called_once_with(
        Name="/apple-health-data/github-pat", WithDecryption=True
    )


@pytest.mark.parametrize("missing", ["GITHUB_OWNER", "GITHUB_REPO", "SSM_PARAM_NAME"])
def test_missing_env_var_raises(monkeypatch, missing):
    monkeypatch.setattr(trigger_refresh, "_ssm_client", _mock_ssm())
    requests = _patch_urlopen(monkeypatch, status=204)
    monkeypatch.delenv(missing)

    with pytest.raises(KeyError, match=missing):
        trigger_refresh.lambda_handler(S3_EVENT, None)

    assert requests == []  # dispatch never attempted


def test_ssm_failure_raises(monkeypatch):
    ssm = MagicMock()
    ssm.get_parameter.side_effect = Exception("ParameterNotFound")
    monkeypatch.setattr(trigger_refresh, "_ssm_client", ssm)
    requests = _patch_urlopen(monkeypatch, status=204)

    with pytest.raises(Exception, match="ParameterNotFound"):
        trigger_refresh.lambda_handler(S3_EVENT, None)

    assert requests == []  # dispatch never attempted
