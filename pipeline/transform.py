"""Turn raw AlphaVantage JSON into rows that match our database tables."""
from datetime import date
from decimal import Decimal, InvalidOperation

# Longest normal gap between trading days is ~4 days (weekend + holiday)
MAX_STALENESS_DAYS = 7

# Database column -> AlphaVantage key, for each price in a daily bar
PRICE_FIELDS = {"open": "1. open", "high": "2. high", "low": "3. low", "close": "4. close"}


class ValidationError(Exception):
    pass


def _to_price(value: str) -> Decimal:
    # Decimal, not float: 30.51 is stored exactly, matching the NUMERIC column
    price = Decimal(value)
    if not price.is_finite():
        raise ValueError(f"not a finite number: {value!r}")
    return price


def _parse_daily_bar(symbol: str, day: str, bar: dict) -> dict:
    # Step 1: convert text to proper types. Anything unparseable is rejected.
    try:
        row = {"symbol": symbol, "trade_date": date.fromisoformat(day)}
        for column, key in PRICE_FIELDS.items():
            row[column] = _to_price(bar[key])
        row["volume"] = int(bar["5. volume"])
    except (KeyError, ValueError, InvalidOperation) as e:
        raise ValidationError(f"{symbol} {day}: unparseable bar ({e!r})") from e

    # Step 2: check the values make sense (same rules as the CHECK constraints)
    if min(row["open"], row["high"], row["low"], row["close"]) <= 0:
        raise ValidationError(f"{symbol} {day}: non-positive price")
    if row["volume"] < 0:
        raise ValidationError(f"{symbol} {day}: negative volume")
    if row["low"] > min(row["open"], row["close"]) or row["high"] < max(row["open"], row["close"]):
        raise ValidationError(f"{symbol} {day}: open/close outside the low-high range")
    return row


def to_daily_price_rows(symbol: str, series: dict) -> tuple[list[dict], list[str]]:
    """Return (valid rows, reasons for each rejected day). One bad day doesn't sink the rest."""
    rows, rejected = [], []
    for day, bar in series.items():
        try:
            rows.append(_parse_daily_bar(symbol, day, bar))
        except ValidationError as e:
            rejected.append(str(e))
    return rows, rejected


def check_freshness(symbol: str, rows: list[dict], today: date) -> None:
    """Dataset-level check: every bar can be valid while the data as a whole is stale."""
    newest = max(row["trade_date"] for row in rows)
    age_days = (today - newest).days
    if age_days > MAX_STALENESS_DAYS:
        raise ValidationError(f"{symbol}: newest bar is {newest} ({age_days} days old), data looks stale")
