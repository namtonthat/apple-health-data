import json
import requests
import pytest

RAW_AUTO_EXPORT = "../source/apple-health/HealthAutoExport-2022-12-25-2023-03-25.json"


def sync_apple_health_data():
    with open(RAW_AUTO_EXPORT, "r") as ae:
        raw_data = json.loads(ae.read())

    requests.post("http://localhost:8082/syncs", json=raw_data)


@pytest.fixture
def raw_data_fixture():
    with open(RAW_AUTO_EXPORT, "r") as ae:
        raw_data = json.loads(ae.read())
    return raw_data


def test_sync_apple_health_data(mocker, raw_data_fixture):
    # Mock the json.loads and requests.post functions
    mocker.patch("json.loads")
    mocker.patch("requests.post")

    expected_data = raw_data_fixture

    sync_apple_health_data()

    # Verify the json.loads call
    json.loads.assert_called_once_with(expected_data)

    # Verify the requests.post call
    requests.post.assert_called_once_with(
        "http://localhost:8082/syncs", json=expected_data
    )
