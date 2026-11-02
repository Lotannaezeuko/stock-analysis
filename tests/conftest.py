import json
import os
from datetime import date
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import psycopg2
import pytest

FIXTURES = Path(__file__).parent / "fixtures"
SQL_DIR = Path(__file__).resolve().parent.parent / "pipeline" / "sql"

# The PFE fixture's newest bar is 2026-10-30; tests pretend "today" is shortly after
FIXTURE_TODAY = date(2026, 11, 2)


@pytest.fixture
def daily_response() -> dict:
    """A real TIME_SERIES_DAILY response for PFE (100 trading days)."""
    return json.loads((FIXTURES / "time_series_daily_pfe.json").read_text())


@pytest.fixture
def daily_series(daily_response) -> dict:
    return daily_response["Time Series (Daily)"]


@pytest.fixture
def fake_api(monkeypatch, daily_response):
    """Replace AlphaVantage with canned responses: no network, no API quota, no waiting.

    Every symbol gets the PFE fixture unless overridden via fake_api.responses[symbol].
    """
    api = SimpleNamespace(responses={}, calls=[])

    def fake_get(url, params, timeout):
        api.calls.append(params)
        res = MagicMock()
        res.json.return_value = api.responses.get(params["symbol"], daily_response)
        return res

    class FixedDate(date):
        @classmethod
        def today(cls):
            return FIXTURE_TODAY

    monkeypatch.setattr("pipeline.extract.requests.get", fake_get)
    monkeypatch.setattr("pipeline.extract.time.sleep", lambda seconds: None)
    monkeypatch.setattr("pipeline.run.date", FixedDate)
    return api


@pytest.fixture
def db_url() -> str:
    url = os.getenv("TEST_DATABASE_URL")
    if not url:
        pytest.skip("TEST_DATABASE_URL not set; skipping database tests")
    return url


@pytest.fixture
def db(db_url):
    """A fresh copy of the real schema + seed data for every test."""
    conn = psycopg2.connect(db_url)
    # Guard rail: this fixture wipes the database, so refuse anything not named *_test
    with conn, conn.cursor() as cur:
        cur.execute("SELECT current_database()")
        dbname = cur.fetchone()[0]
    if not dbname.endswith("_test"):
        conn.close()
        pytest.fail(f"TEST_DATABASE_URL must point at a database ending in _test, got {dbname!r}")

    with conn, conn.cursor() as cur:
        cur.execute("DROP SCHEMA public CASCADE; CREATE SCHEMA public;")
        cur.execute((SQL_DIR / "schema.sql").read_text())
        cur.execute((SQL_DIR / "seed_symbols.sql").read_text())
    yield conn
    conn.close()
