"""Integration tests against a real PostgreSQL database.

Skipped unless TEST_DATABASE_URL points at a database whose name ends in _test.
"""
from decimal import Decimal

import psycopg2
import pytest

from pipeline.load import upsert_daily_prices
from pipeline.run import run, run_status
from pipeline.transform import to_daily_price_rows


def query(conn, sql, params=None):
    with conn, conn.cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchall()


@pytest.fixture
def pfe_rows(daily_series):
    rows, _ = to_daily_price_rows("PFE", daily_series)
    return rows


# ---------------------------------------------------------------- load


def test_loading_the_same_data_twice_does_not_duplicate(db, pfe_rows):
    upsert_daily_prices(db, pfe_rows)
    upsert_daily_prices(db, pfe_rows)

    assert query(db, "SELECT count(*) FROM daily_prices") == [(100,)]


def test_reloading_a_revised_bar_updates_it(db, pfe_rows):
    upsert_daily_prices(db, pfe_rows)
    newest = max(pfe_rows, key=lambda r: r["trade_date"])
    newest["close"] = Decimal("30.6000")

    upsert_daily_prices(db, pfe_rows)

    assert query(db, "SELECT close FROM daily_prices WHERE trade_date = %s", (newest["trade_date"],)) == [
        (Decimal("30.6000"),)
    ]


def test_database_rejects_impossible_bars_and_rolls_back_the_batch(db, pfe_rows):
    # Bypass Python validation to prove the CHECK constraint is a real safety net
    pfe_rows[0]["high"] = pfe_rows[0]["low"] - 1

    with pytest.raises(psycopg2.errors.CheckViolation):
        upsert_daily_prices(db, pfe_rows)

    assert query(db, "SELECT count(*) FROM daily_prices") == [(0,)]


def test_prices_for_unknown_symbols_are_rejected(db, pfe_rows):
    rows = [{**r, "symbol": "NOPE"} for r in pfe_rows]

    with pytest.raises(psycopg2.errors.ForeignKeyViolation):
        upsert_daily_prices(db, rows)


# ---------------------------------------------------------------- full run


def test_successful_run_is_recorded_with_lineage(db, db_url, fake_api):
    status = run("fake-key", db_url, only=["AAPL", "MSFT"])

    assert status == "succeeded"
    [(run_id, run_status_, attempted, failed, rows, finished)] = query(
        db, "SELECT run_id, status, symbols_attempted, symbols_failed, rows_loaded, finished_at FROM pipeline_runs"
    )
    assert (run_status_, attempted, failed, rows) == ("succeeded", 2, 0, 200)
    assert finished is not None
    # Every loaded row points back to the run that wrote it
    assert query(db, "SELECT DISTINCT run_id FROM daily_prices") == [(run_id,)]


def test_one_failing_symbol_makes_the_run_partial(db, db_url, fake_api):
    fake_api.responses["MSFT"] = {"Information": "rate limit"}

    status = run("fake-key", db_url, only=["AAPL", "MSFT"])

    assert status == "partial"
    [(attempted, failed, error)] = query(db, "SELECT symbols_attempted, symbols_failed, error FROM pipeline_runs")
    assert (attempted, failed) == (2, 1)
    assert "MSFT: rate limit" in error
    assert query(db, "SELECT DISTINCT symbol FROM daily_prices") == [("AAPL",)]


def test_stale_data_is_never_loaded(db, db_url, fake_api, daily_response):
    old_days = {d: bar for d, bar in daily_response["Time Series (Daily)"].items() if d <= "2026-06-16"}
    fake_api.responses["JPM"] = {"Time Series (Daily)": old_days}

    status = run("fake-key", db_url, only=["JPM"])

    assert status == "failed"
    assert query(db, "SELECT count(*) FROM daily_prices") == [(0,)]


def test_inactive_symbols_are_skipped(db, db_url, fake_api):
    run("fake-key", db_url, only=["AAPL", "LUV"])  # LUV is paused in the seed

    assert [c["symbol"] for c in fake_api.calls] == ["AAPL"]


@pytest.mark.parametrize(
    "attempted, failed, expected",
    [(20, 0, "succeeded"), (20, 3, "partial"), (20, 20, "failed"), (0, 0, "failed")],
)
def test_run_status(attempted, failed, expected):
    assert run_status(attempted, failed) == expected


# ---------------------------------------------------------------- features


def test_rolling_features_are_null_until_the_window_is_full(db, pfe_rows):
    upsert_daily_prices(db, pfe_rows)

    rows = query(db, "SELECT sma_20, volatility_20d, next_day_return FROM price_features ORDER BY trade_date")

    assert all(sma is None for sma, _, _ in rows[:19])
    assert rows[19][0] is not None          # 20th day: first full 20-day window
    assert rows[19][1] is None              # volatility needs 20 *returns* = 21 days
    assert rows[20][1] is not None
    assert rows[-1][2] is None              # no "tomorrow" for the newest day


def test_earnings_are_only_visible_after_they_were_reported(db, pfe_rows):
    upsert_daily_prices(db, pfe_rows)
    # Real PFE report from tests/fixtures/earnings_pfe.json: Q2 published 2026-08-04
    query(
        db,
        "INSERT INTO quarterly_earnings (symbol, fiscal_date_ending, reported_date, reported_eps)"
        " VALUES ('PFE', '2026-06-30', '2026-08-04', 0.77) RETURNING 1",
    )

    features = dict(
        query(db, "SELECT trade_date::text, last_reported_eps FROM price_features WHERE trade_date BETWEEN '2026-08-03' AND '2026-08-05'")
    )

    # No look-ahead: the number isn't known on the day it's published, only from the next day
    assert features == {"2026-08-03": None, "2026-08-04": None, "2026-08-05": Decimal("0.7700")}
