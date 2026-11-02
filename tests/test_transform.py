from datetime import date
from decimal import Decimal

import pytest

from pipeline.transform import ValidationError, check_freshness, to_daily_price_rows

GOOD_BAR = {"1. open": "30", "2. high": "31", "3. low": "29", "4. close": "30.5", "5. volume": "100"}


def test_real_response_parses_every_day(daily_series):
    rows, rejected = to_daily_price_rows("PFE", daily_series)

    assert len(rows) == 100
    assert rejected == []


def test_values_are_converted_to_exact_types(daily_series):
    rows, _ = to_daily_price_rows("PFE", daily_series)
    newest = next(r for r in rows if r["trade_date"] == date(2026, 10, 30))

    assert newest == {
        "symbol": "PFE",
        "trade_date": date(2026, 10, 30),
        "open": Decimal("30.5100"),
        "high": Decimal("30.6700"),
        "low": Decimal("30.1400"),
        "close": Decimal("30.5200"),
        "volume": 45485398,
    }


@pytest.mark.parametrize(
    "day, bar, reason",
    [
        ("2026-10-01", {**GOOD_BAR, "2. high": "28"}, "outside the low-high range"),
        ("2026-10-01", {**GOOD_BAR, "3. low": "30.6"}, "outside the low-high range"),
        ("2026-10-01", {**GOOD_BAR, "4. close": "-1"}, "non-positive price"),
        ("2026-10-01", {**GOOD_BAR, "1. open": "0"}, "non-positive price"),
        ("2026-10-01", {**GOOD_BAR, "5. volume": "-5"}, "negative volume"),
        ("2026-10-01", {**GOOD_BAR, "4. close": "abc"}, "unparseable"),
        ("2026-10-01", {**GOOD_BAR, "4. close": "NaN"}, "unparseable"),
        ("2026-10-01", {k: v for k, v in GOOD_BAR.items() if k != "5. volume"}, "unparseable"),
        ("not-a-date", GOOD_BAR, "unparseable"),
    ],
)
def test_invalid_bars_are_rejected_with_a_reason(day, bar, reason):
    rows, rejected = to_daily_price_rows("TEST", {day: bar})

    assert rows == []
    assert len(rejected) == 1
    assert reason in rejected[0]
    assert rejected[0].startswith(f"TEST {day}")


def test_one_bad_day_does_not_reject_the_rest():
    series = {"2026-10-01": GOOD_BAR, "2026-10-02": {**GOOD_BAR, "2. high": "1"}, "2026-10-05": GOOD_BAR}

    rows, rejected = to_daily_price_rows("TEST", series)

    assert [r["trade_date"] for r in rows] == [date(2026, 10, 1), date(2026, 10, 5)]
    assert len(rejected) == 1


@pytest.mark.parametrize("today", [date(2026, 10, 30), date(2026, 11, 2), date(2026, 11, 6)])
def test_recent_data_passes_freshness_check(daily_series, today):
    rows, _ = to_daily_price_rows("PFE", daily_series)

    check_freshness("PFE", rows, today=today)  # newest bar is 2026-10-30


def test_stale_data_fails_freshness_check(daily_series):
    rows, _ = to_daily_price_rows("PFE", daily_series)

    with pytest.raises(ValidationError, match="looks stale"):
        check_freshness("PFE", rows, today=date(2026, 11, 7))
