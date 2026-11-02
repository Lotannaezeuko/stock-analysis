import time

import requests

BASE_URL = "https://www.alphavantage.co/query"
TIMEOUT_SECONDS = 30
# Free tier allows 1 request per second. 1.1s still tripped the limit on the
# first live run (network jitter), so leave generous headroom.
MIN_SECONDS_BETWEEN_CALLS = 2

_last_call_at = 0.0


class ExtractError(Exception):
    pass


def _call_api(params: dict, api_key: str) -> dict:
    global _last_call_at

    # Wait if the previous call was less than MIN_SECONDS_BETWEEN_CALLS ago
    wait = MIN_SECONDS_BETWEEN_CALLS - (time.monotonic() - _last_call_at)
    if wait > 0:
        time.sleep(wait)
    _last_call_at = time.monotonic()

    res = requests.get(BASE_URL, params={**params, "apikey": api_key}, timeout=TIMEOUT_SECONDS)
    res.raise_for_status()
    return res.json()


def _error_reason(data: dict) -> str:
    # AlphaVantage returns HTTP 200 even for errors and rate limits; the
    # problem is described in a "Note", "Information" or "Error Message" key.
    return data.get("Note") or data.get("Information") or data.get("Error Message") or "unexpected response"


def fetch_daily_prices(symbol: str, api_key: str) -> dict:
    """Return the last ~100 trading days as {"2026-10-30": {"1. open": "30.51", ...}, ...}."""
    data = _call_api({"function": "TIME_SERIES_DAILY", "symbol": symbol, "outputsize": "compact"}, api_key)
    if "Time Series (Daily)" not in data:
        raise ExtractError(f"{symbol}: {_error_reason(data)}")
    return data["Time Series (Daily)"]
