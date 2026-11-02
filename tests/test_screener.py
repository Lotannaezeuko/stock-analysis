"""The screener app's SQL, run against the real schema (needs TEST_DATABASE_URL)."""
from decimal import Decimal

import pandas as pd
import pytest

from pipeline.load import upsert_daily_prices
from pipeline.transform import to_daily_price_rows
from screener import build_query

NO_FILTERS = {
    "sector": "", "min_pe": None, "max_pe": None, "min_div": None, "min_mcap": None,
    "min_eps": None, "max_pb": None, "max_debt": None, "sort_by": "close", "order": "desc",
}


@pytest.fixture
def loaded(db, daily_series):
    """AAPL and PFE have prices (same fixture data); only AAPL has fundamentals."""
    rows, _ = to_daily_price_rows("PFE", daily_series)
    upsert_daily_prices(db, rows)
    upsert_daily_prices(db, [{**r, "symbol": "AAPL"} for r in rows])
    with db, db.cursor() as cur:
        cur.execute("INSERT INTO stock_fundamentals (symbol, name, pe_ratio) VALUES ('AAPL', 'Apple Inc', 31.2)")
    return db


def screen(conn, **filters):
    query, params = build_query({**NO_FILTERS, **filters})
    return pd.read_sql_query(query, conn, params=params)


def test_latest_prices_has_the_newest_bar_and_daily_change(loaded, daily_series):
    with loaded, loaded.cursor() as cur:
        cur.execute("SELECT trade_date::text, close, change_pct FROM latest_prices WHERE symbol = 'PFE'")
        trade_date, close, change_pct = cur.fetchone()

    previous_close = Decimal(daily_series["2026-10-29"]["4. close"])
    assert (trade_date, close) == ("2026-10-30", Decimal("30.5200"))
    assert change_pct == pytest.approx(Decimal("30.52") / previous_close - 1)


def test_screener_lists_every_active_stock_with_prices_where_loaded(loaded):
    df = screen(loaded)

    assert len(df) == 20  # all active symbols in the seed
    assert set(df.loc[df["close"].notna(), "symbol"]) == {"AAPL", "PFE"}


def test_fundamental_filters_only_match_stocks_with_a_snapshot(loaded):
    df = screen(loaded, max_pe=40)

    assert df["symbol"].tolist() == ["AAPL"]


def test_sector_filter_uses_the_pipeline_sectors(loaded):
    df = screen(loaded, sector="information technology")

    assert set(df["symbol"]) == {"AAPL", "MSFT", "NVDA", "ORCL", "STX"}


def test_unknown_sort_column_falls_back_safely(loaded):
    df = screen(loaded, sort_by="close; DROP TABLE symbols")

    assert len(df) == 20
