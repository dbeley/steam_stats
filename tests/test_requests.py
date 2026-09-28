"""Tests for steam_stats.requests."""

import json
from typing import cast

import pytest
import requests
from requests.adapters import HTTPAdapter

from steam_stats.requests import (
    create_session,
    get_steam_json,
    redact_url,
    safe_json_response,
)


class FakeResponse:
    def __init__(self, status_code=200, json_data=None, text=None, bad_json=False):
        self.status_code = status_code
        self._json_data = json_data
        self._bad_json = bad_json
        self.url = "https://api.steampowered.com/endpoint?key=SECRET&steamid=USER"
        if text is None:
            text = "" if json_data is None else json.dumps(json_data)
        self.text = text

    def json(self):
        if self._bad_json:
            raise requests.exceptions.JSONDecodeError("bad json", "", 0)
        return self._json_data

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.exceptions.HTTPError(f"HTTP {self.status_code}")


class FakeSession:
    """Returns queued responses; the last one repeats indefinitely."""

    def __init__(self, *responses):
        self._responses = list(responses)
        self.calls = 0

    def get(self, url, timeout=None):
        self.calls += 1
        if len(self._responses) > 1:
            return self._responses.pop(0)
        return self._responses[0]


class ExplodingSession:
    def __init__(self, error=None):
        self.calls = 0
        self._error = error or requests.exceptions.ConnectionError("boom")

    def get(self, url, timeout=None):
        self.calls += 1
        raise self._error


# ---------------------------------------------------------------------------
# redact_url
# ---------------------------------------------------------------------------


def test_redact_url_masks_key_and_steamid():
    url = "https://api.steampowered.com/x?key=SECRET&steamid=USER&appid=70"
    redacted = redact_url(url)
    assert "SECRET" not in redacted
    assert "USER" not in redacted
    assert "REDACTED" in redacted
    assert "appid=70" in redacted


def test_redact_url_case_insensitive():
    assert "SECRET" not in redact_url("https://x/?KEY=SECRET")


def test_redact_url_without_query_unchanged():
    url = "https://store.steampowered.com/appreviews/70?json=1"
    assert "SECRET" not in redact_url(url)
    assert redact_url("https://store.steampowered.com/app/70") == (
        "https://store.steampowered.com/app/70"
    )


# ---------------------------------------------------------------------------
# create_session
# ---------------------------------------------------------------------------


def test_create_session_retry_config():
    session = create_session(workers=50)
    adapter = cast(HTTPAdapter, session.get_adapter("https://example.com"))
    assert adapter.max_retries.total == 5
    assert 429 in adapter.max_retries.status_forcelist
    assert adapter._pool_maxsize >= 50


# ---------------------------------------------------------------------------
# safe_json_response
# ---------------------------------------------------------------------------


def test_safe_json_response_valid():
    response = FakeResponse(json_data={"a": 1})
    assert safe_json_response(cast(requests.Response, response)) == {"a": 1}


def test_safe_json_response_invalid_returns_none():
    response = FakeResponse(bad_json=True, text="{not json")
    assert safe_json_response(cast(requests.Response, response)) is None


# ---------------------------------------------------------------------------
# get_steam_json
# ---------------------------------------------------------------------------


def test_get_steam_json_success():
    session = FakeSession(FakeResponse(json_data={"playerstats": {}}))
    assert get_steam_json(session, "http://x", "70") == {"playerstats": {}}


def test_get_steam_json_404_with_json_body_is_parsed():
    body = {"playerstats": {"error": "Requested app has no stats"}}
    session = FakeSession(FakeResponse(status_code=404, json_data=body))
    result = get_steam_json(session, "http://x", "70")
    assert result == body


def test_get_steam_json_404_without_body_returns_error():
    session = FakeSession(FakeResponse(status_code=404, text=""))
    result = get_steam_json(session, "http://x", "70")
    assert result["70"]["success"] is False
    assert result["70"]["error"] == "HTTP 404"


def test_get_steam_json_rate_limit_returns_error():
    # Retries live in the session adapter; get_steam_json inspects the result.
    session = FakeSession(FakeResponse(status_code=429, text=""))
    result = get_steam_json(session, "http://x", "70")
    assert result["70"]["error"] == "HTTP 429"
    assert session.calls == 1


def test_get_steam_json_server_error_returns_error():
    session = FakeSession(FakeResponse(status_code=503, text=""))
    result = get_steam_json(session, "http://x", "70")
    assert result["70"]["error"] == "HTTP 503"


def test_get_steam_json_network_error_returns_error():
    session = ExplodingSession()
    result = get_steam_json(session, "http://x", "70")
    assert result["70"]["success"] is False
    assert "boom" in result["70"]["error"]
    assert session.calls == 1


def test_get_steam_json_retry_error_is_caught():
    session = ExplodingSession(requests.exceptions.RetryError("retries exhausted"))
    result = get_steam_json(session, "http://x", "70")
    assert result["70"]["success"] is False
    assert "retries exhausted" in result["70"]["error"]


def test_get_steam_json_empty_body_returns_error():
    session = FakeSession(FakeResponse(status_code=200, text=""))
    result = get_steam_json(session, "http://x", "70")
    assert result["70"]["error"] == "Empty response"


def test_get_steam_json_invalid_json_returns_error():
    session = FakeSession(FakeResponse(status_code=200, bad_json=True, text="oops"))
    result = get_steam_json(session, "http://x", "70")
    assert result["70"]["error"] == "Invalid JSON"


@pytest.mark.parametrize("code", [500, 502, 503, 504])
def test_get_steam_json_various_server_errors(code):
    session = FakeSession(FakeResponse(status_code=code, text=""))
    result = get_steam_json(session, "http://x", "70")
    assert result["70"]["error"] == f"HTTP {code}"
