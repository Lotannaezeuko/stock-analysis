from psycopg2.extras import execute_values

# Upsert: insert new days; for days we already have, overwrite with the latest
# values (the most recent bar can be revised after we first fetch it).
UPSERT_DAILY_PRICES = """
    INSERT INTO daily_prices (symbol, trade_date, open, high, low, close, volume)
    VALUES %s
    ON CONFLICT (symbol, trade_date) DO UPDATE SET
        open = EXCLUDED.open,
        high = EXCLUDED.high,
        low = EXCLUDED.low,
        close = EXCLUDED.close,
        volume = EXCLUDED.volume,
        loaded_at = now();
"""

DAILY_PRICE_TEMPLATE = "(%(symbol)s, %(trade_date)s, %(open)s, %(high)s, %(low)s, %(close)s, %(volume)s)"


def upsert_daily_prices(conn, rows: list[dict]) -> int:
    """Save all rows for one symbol in a single transaction. Returns the number of rows written."""
    if not rows:
        return 0
    # `with conn` = one transaction: all rows commit together, or none do.
    # execute_values sends every row in one statement instead of one per row.
    with conn, conn.cursor() as cur:
        execute_values(cur, UPSERT_DAILY_PRICES, rows, template=DAILY_PRICE_TEMPLATE)
    return len(rows)
