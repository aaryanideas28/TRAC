from unittest.mock import Mock

import pytest
import requests

from railradar.client import RailRadarClient
from railradar.config import Settings
from railradar.exceptions import (
    AuthenticationError,
    InvalidJsonError,
    NotFoundError,
    RateLimitError,
    RequestTimeoutError,
    UpstreamServiceError,
)


def client_for(response=None, *, side_effect=None, retry_count=0, sleeps=None):
    session = Mock()
    if side_effect is not None:
        session.get.side_effect = side_effect
    else:
        session.get.return_value = response
    settings = Settings("secret-key", retry_count=retry_count, retry_delay=0.01)
    sleeper = sleeps.append if sleeps is not None else (lambda _: None)
    return RailRadarClient(settings, session=session, sleeper=sleeper), session


def response(status, payload=None, *, json_error=False, headers=None):
    item = Mock()
    item.status_code = status
    item.headers = headers or {}
    if json_error:
        item.json.side_effect = ValueError("bad json")
    else:
        item.json.return_value = payload
    return item


def test_successful_response_uses_bearer_auth_and_returns_json():
    client, session = client_for(response(200, {"success": True, "data": {}}))

    result = client.get_station_directory()

    assert result["success"] is True
    kwargs = session.get.call_args.kwargs
    assert kwargs["headers"]["Authorization"] == "Bearer secret-key"
    assert kwargs["timeout"] == 15.0


def test_supported_discovery_endpoints_use_documented_paths():
    client, session = client_for(response(200, {"success": True, "data": {}}))

    client.get_local_trains("Mumbai")
    assert session.get.call_args.kwargs["params"] == {"city": "Mumbai"}
    client.get_station_live_board("CSMT", hours=4, include_intermediate=True)
    call = session.get.call_args
    assert call.args[0].endswith("/stations/CSMT/live")
    assert call.kwargs["params"] == {"hours": 4, "includeIntermediate": "true"}


@pytest.mark.parametrize(
    ("status", "error_type"),
    [(401, AuthenticationError), (404, NotFoundError), (429, RateLimitError)],
)
def test_expected_http_errors_are_distinguished(status, error_type):
    client, _ = client_for(response(status, {"success": False, "error": {"message": "problem"}}))

    with pytest.raises(error_type) as caught:
        client.get_station_directory()

    assert caught.value.status_code == status


def test_503_retries_then_raises():
    sleeps = []
    client, session = client_for(
        side_effect=None,
        retry_count=2,
        sleeps=sleeps,
    )
    session.get.side_effect = [
        response(503, {"error": {"message": "temporary"}}),
        response(503, {"error": {"message": "temporary"}}),
        response(503, {"error": {"message": "temporary"}}),
    ]

    with pytest.raises(UpstreamServiceError):
        client.get_station_directory()

    assert session.get.call_count == 3
    assert sleeps == [0.01, 0.02]


def test_timeout_retries_then_raises():
    sleeps = []
    client, _ = client_for(
        side_effect=requests.exceptions.Timeout(), retry_count=1, sleeps=sleeps
    )

    with pytest.raises(RequestTimeoutError):
        client.get_station_directory()

    assert sleeps == [0.01]


def test_malformed_json_is_reported():
    client, _ = client_for(response(200, json_error=True))

    with pytest.raises(InvalidJsonError):
        client.get_station_directory()


def test_429_uses_retry_after_header_before_failing():
    sleeps = []
    client, session = client_for(retry_count=1, sleeps=sleeps)
    session.get.side_effect = [
        response(429, {"error": {"message": "slow down"}}, headers={"Retry-After": "3"}),
        response(429, {"error": {"message": "slow down"}}),
    ]

    with pytest.raises(RateLimitError):
        client.get_station_directory()

    assert sleeps == [3.0]
