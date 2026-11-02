from unittest.mock import MagicMock

import pytest
import requests

from pipeline import extract


@pytest.fixture
def http(monkeypatch):
    """Fake requests.get: set http.response to control what the 'API' returns."""
    state = MagicMock()
    state.calls = []
    state.sleeps = []

    def fake_get(url, params, timeout):
        state.calls.append({"url": url, "params": params, "timeout": timeout})
        return state.response

    monkeypatch.setattr(extract.requests, "get", fake_get)
    monkeypatch.setattr(extract.time, "sleep", state.sleeps.append)
    monkeypatch.setattr(extract, "_last_call_at", 0.0)
    return state


def respond_with(http, payload):
    http.response = MagicMock()
    http.response.json.return_value = payload


def test_returns_the_daily_series_and_sends_the_right_request(http, daily_response):
    respond_with(http, daily_response)

    series = extract.fetch_daily_prices("PFE", "my-key")

    assert len(series) == 100
    assert "2026-10-30" in series
    call = http.calls[0]
    assert call["params"] == {
        "function": "TIME_SERIES_DAILY",
        "symbol": "PFE",
        "outputsize": "compact",
        "apikey": "my-key",
    }
    assert call["timeout"] == extract.TIMEOUT_SECONDS


@pytest.mark.parametrize("key", ["Note", "Information", "Error Message"])
def test_api_errors_sent_with_http_200_are_raised(http, key):
    # AlphaVantage reports rate limits and bad symbols inside a normal-looking response
    respond_with(http, {key: "You have hit the rate limit"})

    with pytest.raises(extract.ExtractError, match="MMM: You have hit the rate limit"):
        extract.fetch_daily_prices("MMM", "my-key")


def test_unexpected_response_shape_is_raised(http):
    respond_with(http, {})

    with pytest.raises(extract.ExtractError, match="unexpected response"):
        extract.fetch_daily_prices("PFE", "my-key")


def test_http_errors_are_raised(http):
    respond_with(http, {})
    http.response.raise_for_status.side_effect = requests.HTTPError("503 Service Unavailable")

    with pytest.raises(requests.HTTPError):
        extract.fetch_daily_prices("PFE", "my-key")


def test_back_to_back_calls_are_spaced_out(http, daily_response):
    respond_with(http, daily_response)

    extract.fetch_daily_prices("PFE", "my-key")
    extract.fetch_daily_prices("MMM", "my-key")

    # First call goes straight out; the second waits ~MIN_SECONDS_BETWEEN_CALLS
    assert len(http.sleeps) == 1
    assert http.sleeps[0] == pytest.approx(extract.MIN_SECONDS_BETWEEN_CALLS, abs=0.2)
