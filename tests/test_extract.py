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


def test_http_errors_are_raised_without_leaking_the_key(http):
    respond_with(http, {})
    http.response.raise_for_status.side_effect = requests.HTTPError(
        "503 Server Error for url: https://www.alphavantage.co/query?symbol=PFE&apikey=my-key"
    )

    with pytest.raises(extract.ExtractError) as error:
        extract.fetch_daily_prices("PFE", "my-key")

    assert "my-key" not in str(error.value)
    assert "PFE: request failed: 503" in str(error.value)
    assert error.value.__cause__ is None and error.value.__suppress_context__  # original error dropped


def test_network_errors_are_raised_as_extract_errors(http, monkeypatch):
    def unreachable(url, params, timeout):
        raise requests.ConnectionError("Failed to establish a new connection")

    monkeypatch.setattr(extract.requests, "get", unreachable)

    with pytest.raises(extract.ExtractError, match="PFE: request failed: Failed to establish"):
        extract.fetch_daily_prices("PFE", "my-key")


def test_api_key_is_redacted_from_api_error_messages(http, daily_quota_response):
    respond_with(http, daily_quota_response)  # message contains "fake-key"

    with pytest.raises(extract.ExtractError) as error:
        extract.fetch_daily_prices("PFE", "fake-key")

    assert "fake-key" not in str(error.value)
    assert "your API key as ***" in str(error.value)


def test_daily_quota_message_is_recognised(http, daily_quota_response):
    respond_with(http, daily_quota_response)

    with pytest.raises(extract.DailyQuotaExceeded):
        extract.fetch_daily_prices("PFE", "fake-key")


def test_per_second_burst_limit_is_not_mistaken_for_the_daily_quota(http, burst_limit_response):
    # The burst message also mentions "25 requests per day", but it's only temporary
    respond_with(http, burst_limit_response)

    with pytest.raises(extract.ExtractError) as error:
        extract.fetch_daily_prices("PFE", "fake-key")

    assert not isinstance(error.value, extract.DailyQuotaExceeded)


def test_back_to_back_calls_are_spaced_out(http, daily_response):
    respond_with(http, daily_response)

    extract.fetch_daily_prices("PFE", "my-key")
    extract.fetch_daily_prices("MMM", "my-key")

    # First call goes straight out; the second waits ~MIN_SECONDS_BETWEEN_CALLS
    assert len(http.sleeps) == 1
    assert http.sleeps[0] == pytest.approx(extract.MIN_SECONDS_BETWEEN_CALLS, abs=0.2)
